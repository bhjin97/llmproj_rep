from dotenv import load_dotenv
import os
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
print("API Key configured:", "OPENAI_API_KEY" in os.environ)

#랭체인
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model='gpt-4o-mini')

def investment_report(symbol, company, stock):
  prompt = ChatPromptTemplate.from_messages(
    [
      ('system', '''
            Want assistance provided by qualified individuals enabled with experience on understanding charts 
            using technical analysis tools while interpreting macroeconomic environment prevailing across world 
            consequently assisting customers acquire long term advantages requires clear verdicts 
            therefore seeking same through informed predictions written down precisely!
        '''),
      ('user', '''
            {company}에 주식을 투자하려고 합니다. 아래의 기본정보, 재무제표를 참고해 마크다운 형식의 투자 보고서를 한글로 작성하세요.
            
            - 기본정보 : 
            {business_info}
            
            - 재무제표 : 
            {financial_statements}
       ''')
    ]
  )
  output_parser = StrOutputParser()
  
  chain = prompt | llm | output_parser
  response = chain.invoke({
    'company':company,
    'business_info': stock.get_basic_info(),
    'financial_statements': stock.get_financial_statement()
  })
  
  return response