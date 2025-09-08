#pip install yfinance

import yfinance as yf
import pandas as pd

class StockInfo():
  def __init__(self, symbol):
    self.symbol = symbol
    self.ticker = yf.Ticker(symbol)
  
  def get_basic_info(self):
    basic_info = pd.DataFrame.from_dict(
      self.ticker.info, orient='index', columns=['Value']
    )
    return basic_info.loc[['longName', 'industry', 'sector', 'marketCap', 'sharesOutstanding']].to_markdown()
  
  def get_financial_statement(self):
    return f"""
        ### Quarterly Income Statement
{self.ticker.quarterly_income_stmt.loc[['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income']].to_markdown()}

        ### Quarterly Balance Sheet
{self.ticker.quarterly_balance_sheet.loc[['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity']].to_markdown()}

        ### Quarterly Cash Flow
{self.ticker.quarterly_cash_flow.loc[['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow']].to_markdown()}
        """


if __name__ == "__main__":
  stock = StockInfo("MSFT")
  print(stock.get_basic_info())
  print(stock.get_financial_statement())