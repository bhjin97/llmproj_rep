import meilisearch 
client = meilisearch.Client('http://127.0.0.1:7700/', 'Gvxls8XI5FkmmwQq4C8cA1IemhT04rbXrXM1bemIDGs')

def stock_search(query):
    return client.index('nasdaq').search('appl')
    