# F&G 데이터의 한계 (미해결)

- 실제 CNN Fear & Greed Index는 2011년부터 존재(2012년 공식 출시, 2011년 1월부터 소급 데이터).
- 오늘 사용한 F&G는 전부 가격에서 역산한 대체 지표이지, CNN 원본 데이터가 아님.
- CNN 원본 daily 데이터는 다음 소스에서 확보 가능(검증됨, fetch 성공):
  - `https://raw.githubusercontent.com/hackingthemarkets/sentiment-fear-and-greed/master/datasets/fear-greed.csv` (2011~2020)
  - `https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2020-09-18` (CNN 공식 API, 2020~현재)
- **다음 작업으로 추천**: 이 두 소스를 실제로 받아서 정확한 F&G 원본으로 전략을 재검증할 것.
