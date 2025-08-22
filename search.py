import meilisearch 
client = meilisearch.Client('http://127.0.0.1:7700/', 'MelVGZiZNWvgfCoR8205-TQZnwbYQRr142Qh1G3lJq8')

def stock_search(query):
    return client.index('nasdaq').search(query)
    