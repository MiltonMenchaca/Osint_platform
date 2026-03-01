from duckduckgo_search import DDGS
import logging

logging.basicConfig(level=logging.DEBUG)

print("Starting DDG test...")
try:
    with DDGS() as ddgs:
        results = list(ddgs.text("site:stackoverflow.com python string formatting", max_results=5))
        print(f"Found {len(results)} results")
        for r in results:
            print(r)
except Exception as e:
    print(f"Error: {e}")
