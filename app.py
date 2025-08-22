import streamlit as st

from search import stock_search
from stock_info import StockInfo
from report_service import investment_report

class SearchResult:
  def __init__(self, item ):
    self.item = item
  
  @property
  def symbol(self):
    return self.item['Symbol']
  @property
  def name(self):
    return self.item['Name']
  def __str__(self):
    return f'{self.symbol}: {self.name}'

st.title('LLM으로 만드는 투자 보고서 생성 서비스')
search_query = st.text_input('회사명', '')

#종목검색결과 리스트
hits_list = stock_search(search_query)['hits']
#print(hits_list)
search_results = [SearchResult(hit) for hit in hits_list]

selected = st.selectbox('검색 결과 목록', search_results)
# 검색전까지는 결과 안보이게
if st.button('검색하기'):
    
    st.header(f'{selected} 기본정보')
    stock = StockInfo(selected.symbol) #ticker
    st.write(stock.get_basic_info()) #기본정보
    st.write(stock.get_financial_statement()) #재무정보

    st.header('투자보고서')
    st.write(investment_report(selected.symbol, selected.name, stock))