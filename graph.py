"""딥리서처 에이전트 — 코디네이터/서브에이전트 구조.

어제 배운 패턴(코디네이터가 일을 구역별로 나눠 서브에이전트에 맡기고, 결과를 합쳐서
점검한 뒤 부족하면 다시 나눠준다)을 LangGraph 없이 `claude_agent_sdk`만으로 구현한다.
로컬 Claude Code 로그인을 그대로 재사용해서 별도 API 키가 필요 없다(my-graph-agent의
agent.py와 같은 방식).

파이프라인: dispatch(구역 판단) → subagents(구역별 조사, 병렬) → aggregate(합성)
          → review(점검) → 부족하면 전 구역으로 한 번 더 dispatch → 최종 답변
"""
import asyncio
import json
import re
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, CLINotFoundError, TextBlock, query
from claude_agent_sdk._errors import ClaudeSDKError

BASE = Path(__file__).parent
CORPUS = json.loads((BASE / "data" / "corpus.json").read_text(encoding="utf-8"))["documents"]
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
CATEGORIES = CONFIG["categories"]  # {category: 설명}

DOCS_BY_CATEGORY = {cat: [] for cat in CATEGORIES}
for doc in CORPUS:
    DOCS_BY_CATEGORY.setdefault(doc["category"], []).append(doc)


def _collect_text(messages) -> str:
    parts = []
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)
    return "".join(parts).strip()


async def _call_llm(prompt: str, system_prompt: str, model: str) -> str:
    """claude_agent_sdk 호출 하나. 실측으로 겪은 문제: 40문항 넘게 연달아 부르면
    가끔(대략 수십 번에 한 번) "Reached maximum number of turns (1)"이라는
    ClaudeSDKError가 일시적으로 난다(재현 조건 불명 — 같은 프롬프트를 다시 부르면
    보통 성공함). 이 하나가 절제실험 전체(40문항)를 통째로 죽이는 걸 실제로 겪어서,
    최대 2회까지 재시도하고 그래도 안 되면 파이프라인을 죽이지 않고 실패를 문자열로
    남긴다(견고성 원칙 — 실패를 숨기지 않되, 다른 문항 처리는 계속 진행)."""
    options = ClaudeAgentOptions(
        model=model, allowed_tools=[], max_turns=CONFIG.get("max_turns", 1),
        setting_sources=[], system_prompt=system_prompt,
    )
    last_error = None
    for attempt in range(3):
        try:
            messages = [msg async for msg in query(prompt=prompt, options=options)]
            return _collect_text(messages)
        except CLINotFoundError:
            import subprocess
            subprocess.run(["npm", "install", "-g", "@anthropic-ai/claude-code"],
                            check=True, capture_output=True, text=True, timeout=120)
        except ClaudeSDKError as e:
            last_error = e
            await asyncio.sleep(1.5 * (attempt + 1))
    return f"[LLM 호출 실패 — {attempt + 1}회 재시도 후에도 실패: {last_error}]"


DISPATCH_SYSTEM_PROMPT = (
    "당신은 리서치 코디네이터입니다. 아래 '구역 목록'과 '질문'을 보고, 이 질문에 답하려면 "
    "어떤 구역(들)의 문서를 조사해야 하는지 판단하세요. 관련 있는 구역이 여러 개일 수 있고, "
    "확실치 않으면 넓게 포함하세요. 반드시 구역 이름만 쉼표로 구분해서 한 줄로 답하세요. "
    "설명이나 다른 텍스트는 절대 쓰지 마세요. 예: tax_law,fabot_log"
)


def _parse_categories(raw: str) -> list[str]:
    found = [c.strip() for c in re.split(r"[,\s]+", raw) if c.strip() in CATEGORIES]
    return sorted(set(found)) or list(CATEGORIES.keys())


async def dispatch(question: str) -> list[str]:
    """코디네이터가 질문을 보고 관련 구역을 고른다(course의 Send() 라우팅에 대응)."""
    if CONFIG["ablation"].get("disable_dispatch_routing"):
        return list(CATEGORIES.keys())
    listing = "\n".join(f"- {cat}: {desc}" for cat, desc in CATEGORIES.items())
    prompt = f"구역 목록:\n{listing}\n\n질문: {question}"
    raw = await _call_llm(prompt, DISPATCH_SYSTEM_PROMPT, CONFIG["coordinator_model"])
    return _parse_categories(raw)


SUBAGENT_SYSTEM_PROMPT = (
    "당신은 리서치 서브에이전트입니다. 아래 '문서 모음'(하나의 구역)에 있는 사실만 근거로 "
    "질문에 답할 수 있는 부분을 찾아 정리하세요. 이 구역 문서로 답할 수 없는 부분은 억지로 "
    "채우지 말고 '이 구역에는 관련 근거 없음'이라고 쓰세요. 답변 끝에 실제로 사용한 문서의 "
    "id를 (문서: id1, id2) 형식으로 표기하세요. 지어내지 마세요."
)


def _category_text(category: str) -> str:
    docs = DOCS_BY_CATEGORY.get(category, [])
    return "\n\n---\n\n".join(f"[문서 id={d['id']}]\n{d['text']}" for d in docs)


async def run_subagent(question: str, category: str) -> dict:
    prompt = f"문서 모음(구역: {category}):\n\n{_category_text(category)}\n\n질문: {question}"
    text = await _call_llm(prompt, SUBAGENT_SYSTEM_PROMPT, CONFIG["subagent_model"])
    return {"category": category, "output": text}


AGGREGATE_SYSTEM_PROMPT = (
    "당신은 리서치 코디네이터입니다. 여러 서브에이전트가 각자 다른 구역 문서를 보고 보내온 "
    "부분 답변들을 종합해서, 질문에 대한 하나의 완결된 한국어 답변을 작성하세요. 서로 다른 "
    "구역의 사실을 연결해서 설명해야 하면 그렇게 하고, 근거 없는 내용은 추측하지 마세요. "
    "\n\n**서브에이전트 답변끼리 결론이 다르면, 여러 관점을 나란히 나열하지 말고 반드시 "
    "조율하세요**: 더 구체적인 근거 문서(실측 데이터·공식 수치 인용)를 가진 답변이, "
    "일반 원칙이나 근거 문서가 없다고 밝힌 답변보다 우선합니다. 정밀한 근거를 댄 결론을 "
    "최종 답의 맨 앞(핵심 결론)에 놓고, 단순 계산이나 정보 부족을 인정한 답변은 "
    "'왜 이 단순 계산은 부정확한지'를 설명하는 보조 설명으로만 쓰세요. 서로 다른 근거 "
    "수준의 답을 동등한 선택지처럼 제시하는 것은 답이 아닙니다. "
    "\n\n**틀린 가정을 지적할 때는 반드시 무엇이 틀렸는지 그 대상을 명확히 쓰세요**: "
    "'이는 세법과 맞지 않습니다'처럼 지시대명사만 쓰면 '통계로 계산한 결론'을 가리키는지 "
    "'단순화한 가정'을 가리키는지 헷갈립니다. '⟨구체적 가정 문장⟩은(는) 세법과 맞지 "
    "않습니다'처럼 그 가정 자체를 다시 한번 명시해서 쓰세요."
    "\n\n답변 끝에 실제로 인용한 문서 id를 모두 (근거 문서: ...) 형식으로 나열하세요."
)


async def aggregate(question: str, partials: list[dict]) -> str:
    joined = "\n\n".join(f"[{p['category']} 구역 서브에이전트 답변]\n{p['output']}" for p in partials)
    prompt = f"질문: {question}\n\n{joined}"
    return await _call_llm(prompt, AGGREGATE_SYSTEM_PROMPT, CONFIG["synthesis_model"])


REVIEW_SYSTEM_PROMPT = (
    "당신은 품질 점검자입니다. 아래 질문과 답변을 보고, 답변이 질문에 실제로 직접적으로 "
    "답하고 있는지, 근거 문서 인용이 있는지 판단하세요. 충분하면 'SUFFICIENT', 불충분하면 "
    "'INSUFFICIENT'라고만 한 단어로 답하세요."
)


async def review(question: str, answer_text: str) -> bool:
    if CONFIG["ablation"].get("disable_review_loop"):
        return True
    prompt = f"질문: {question}\n\n답변:\n{answer_text}"
    verdict = await _call_llm(prompt, REVIEW_SYSTEM_PROMPT, CONFIG["coordinator_model"])
    return "SUFFICIENT" in verdict.upper() and "INSUFFICIENT" not in verdict.upper()


async def answer_async(question: str) -> dict:
    trace = []

    if CONFIG["ablation"].get("single_llm_only"):
        # 절제실험용: 코디네이터/서브에이전트 구조 없이 전체 코퍼스를 한 번에 통째로 던진다.
        all_text = "\n\n---\n\n".join(f"[문서 id={d['id']}]\n{d['text']}" for d in CORPUS)
        prompt = f"전체 문서:\n\n{all_text}\n\n질문: {question}"
        final = await _call_llm(prompt, AGGREGATE_SYSTEM_PROMPT, CONFIG["synthesis_model"])
        return {"question": question, "answer": final, "categories_used": ["ALL(single_llm_only)"],
                "subagent_outputs": [], "trace": "single_llm_only(ablation)"}

    categories = await dispatch(question)
    trace.append(f"dispatch → {categories}")

    partials = await asyncio.gather(*(run_subagent(question, c) for c in categories))
    trace.append(f"subagents({len(partials)}) 완료")

    final = await aggregate(question, partials)
    sufficient = await review(question, final)
    trace.append(f"review → {'SUFFICIENT' if sufficient else 'INSUFFICIENT'}")

    if not sufficient and set(categories) != set(CATEGORIES.keys()):
        # 부족하면 딱 한 번만, 전 구역으로 넓혀서 재시도한다(무한 루프 방지).
        all_categories = list(CATEGORIES.keys())
        partials = await asyncio.gather(*(run_subagent(question, c) for c in all_categories))
        final = await aggregate(question, partials)
        categories = all_categories
        trace.append(f"재dispatch(전 구역) → {categories}")

    return {
        "question": question,
        "answer": final,
        "categories_used": categories,
        "subagent_outputs": partials,
        "trace": " → ".join(trace),
    }


def answer(question: str) -> dict:
    return asyncio.run(answer_async(question))


if __name__ == "__main__":
    import sys
    # Windows PowerShell/cmd 콘솔은 기본 cp949라, 답변에 ⚠ 같은 유니코드 기호가
    # 섞이면 print()가 UnicodeEncodeError로 죽는다(실측으로 겪음) — 모르는 문자는
    # 깨진 채로라도 보이는 게 스크립트가 죽는 것보다 낫다.
    sys.stdout.reconfigure(errors="replace")
    q = " ".join(sys.argv[1:]) or "건강보험 피부양자 자격을 잃게 되는 소득 기준은 얼마인가?"
    result = answer(q)
    print(f"Q: {q}")
    print(f"구역: {result['categories_used']}")
    print(f"경로: {result['trace']}")
    print(f"답변:\n{result['answer']}")
