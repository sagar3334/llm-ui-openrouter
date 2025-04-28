from app import web_search, get_webpage_content

def test_web_search():
    print("Testing web search functionality...")
    query = "Python programming language"
    results = web_search(query)
    print(f"Search results for '{query}':")
    print(results)
    print("\n" + "-"*50 + "\n")

def test_webpage_content():
    print("Testing webpage content fetching...")
    url = "https://python.org"
    content = get_webpage_content(url)
    print(f"Content from {url} (first 500 chars):")
    print(content[:500] + "...")
    print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    test_web_search()
    test_webpage_content()