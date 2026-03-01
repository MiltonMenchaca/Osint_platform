import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
import logging
import random
import time
import json
from abc import ABC, abstractmethod
from duckduckgo_search import DDGS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Mock Base Classes ---

class OSINTToolError(Exception):
    """Base exception for OSINT tool errors"""
    pass

class BaseWrapper(ABC):
    """Base class for all OSINT tool wrappers"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.tool_name = self.get_tool_name()

    @abstractmethod
    def get_tool_name(self) -> str:
        pass

    def _format_output(
        self, results: List[Dict[str, Any]], execution_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format tool output in standard format"""
        metadata: Dict[str, Any] = {
            "result_count": len(results),
        }

        for key, value in execution_info.items():
            if key not in metadata:
                metadata[key] = value

        return {
            "tool": self.tool_name,
            "input_type": execution_info.get("input_type"),
            "input_value": execution_info.get("input_value"),
            "results": results,
            "metadata": metadata,
        }

# --- Google Search Wrapper ---

class GoogleSearchWrapper(BaseWrapper):
    """
    Wrapper for performing Google Searches (Scraping)
    WARNING: This is prone to blocking. Use with caution or rotate proxies.
    """
    
    def __init__(self):
        # Skip BaseWrapper.__init__ validation because this is a script, not a binary
        self.config = {}
        self.tool_name = "google_search"
        self.tool_path = None
        self.temp_dir = None
        
        self.user_agents = [
            # Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            # macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
            # Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
            # Mobile
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/121.0.6167.66 Mobile/15E148 Safari/604.1",
            # Legacy/Compatibility
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        ]

    def get_tool_name(self) -> str:
        return "google_search"

    def is_tool_available(self) -> bool:
        return True

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "string", "query"]

    def get_supported_output_types(self) -> List[str]:
        return ["url"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute Google Search
        Args:
            input_data: {"type": "query", "value": "site:example.com"}
            kwargs: num_results (default 10)
        """
        query = input_data.get("value")
        num_results = kwargs.get("num_results", 10)
        
        if not query:
            raise OSINTToolError("Query is required")

        logger.info(f"Executing Google Search for: {query}")
        
        results = []
        
        # 1. Try Google Scraping
        try:
            results = self._scrape_google(query, num_results)
        except Exception as e:
            logger.warning(f"Google scraping failed: {e}")
            
        # 2. Fallback to DuckDuckGo (All methods) if Google failed
        if not results:
            try:
                results = self._scrape_duckduckgo(query, num_results)
            except Exception as e:
                logger.warning(f"DuckDuckGo scraping failed: {e}")

        execution_info = {
            "input_type": "query",
            "input_value": query,
            "execution_time": 0, # Placeholder
            "command": f"google_search '{query}'",
        }
        
        return self._format_output(results, execution_info)

    def _scrape_google(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        results = []
        session = requests.Session()
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        session.headers.update(headers)
        
        # gbv=1 forces non-JS version (Google Basic Version)
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={num_results}&gbv=1"
        
        # Random delay
        logger.info("Waiting random delay before Google request...")
        time.sleep(random.uniform(2.0, 5.0))
        
        logger.info(f"Requesting URL: {url}")
        response = session.get(url, timeout=15)
        
        if response.status_code == 429:
            raise OSINTToolError("Google blocking detected (HTTP 429)")
            
        if response.status_code != 200:
             raise OSINTToolError(f"Google returned HTTP {response.status_code}")
             
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Check for meta refresh
        meta_refresh = soup.select_one("meta[http-equiv='refresh']")
        if meta_refresh:
            content = meta_refresh.get("content")
            if content and "url=" in content:
                refresh_url = content.split("url=")[1]
                if refresh_url.startswith("/"):
                    refresh_url = "https://www.google.com" + refresh_url
                
                logger.info(f"Following meta refresh to: {refresh_url}")
                time.sleep(2)
                # Use same session to keep cookies
                response = session.get(refresh_url, timeout=15)
                soup = BeautifulSoup(response.text, "html.parser")

        # Parse search results
        found_links = soup.select("a h3")
        logger.info(f"Found {len(found_links)} potential results (h3 inside a)")
        
        if not found_links:
            div_gs = soup.select("div.g")
            logger.info(f"Found {len(div_gs)} div.g elements")
        
        processed_urls = set()
        
        # Strategy 1: Find 'a' tags containing 'h3'
        for h3 in found_links:
            link_tag = h3.find_parent("a")
            if not link_tag: continue
                
            href = link_tag.get("href")
            if not href: continue
                
            if href.startswith("/url?q="):
                href = href.split("/url?q=")[1].split("&")[0]
            
            href = urllib.parse.unquote(href)
            
            if href in processed_urls: continue
            if "google.com" in href or "javascript:void" in href: continue
            
            title = h3.get_text()
            snippet = "No snippet available"
            container = link_tag.find_parent("div")
            if container and container.parent:
                full_text = container.parent.get_text()
                if len(full_text) > len(title):
                    snippet = full_text.replace(title, "").strip()[:200] + "..."

            results.append({
                "type": "url",
                "value": href,
                "properties": {"title": title, "snippet": snippet}
            })
            processed_urls.add(href)

        # Strategy 2: div.g fallback
        if not results:
            for div in soup.select("div.g"):
                link_tag = div.select_one("a")
                if link_tag and link_tag.get("href"):
                    href = link_tag.get("href")
                    if href.startswith("/url?q="):
                        href = href.split("/url?q=")[1].split("&")[0]
                    href = urllib.parse.unquote(href)
                    
                    if href in processed_urls or "google.com" in href: continue

                    title_tag = div.select_one("h3")
                    title = title_tag.get_text() if title_tag else "No Title"
                    
                    snippet_tag = div.select_one("div.s") or div.select_one("div.VwiC3b") or div.select_one("span.st")
                    snippet = snippet_tag.get_text() if snippet_tag else ""
                    
                    results.append({
                        "type": "url",
                        "value": href,
                        "properties": {"title": title, "snippet": snippet}
                    })
                    processed_urls.add(href)
        
        return results

    def _scrape_duckduckgo_html(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        results = []
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Referer": "https://duckduckgo.com/",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        url = "https://html.duckduckgo.com/html/"
        data = {'q': query}
        
        logger.info(f"Requesting DDG HTML: {url}")
        time.sleep(random.uniform(1.0, 2.0))
        response = requests.post(url, data=data, headers=headers, timeout=15)
        
        if response.status_code not in [200, 202]:
             raise OSINTToolError(f"DuckDuckGo HTML returned HTTP {response.status_code}")
             
        soup = BeautifulSoup(response.text, "html.parser")
        
        result_divs = soup.select("div.result")
        logger.info(f"Found {len(result_divs)} DuckDuckGo HTML results")
        
        for div in result_divs:
            if len(results) >= num_results:
                break
                
            title_tag = div.select_one("h2.result__title > a.result__a")
            if not title_tag:
                continue
                
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")
            
            if not href or "duckduckgo.com" in href:
                continue
                
            snippet_tag = div.select_one("a.result__snippet")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            
            results.append({
                "type": "url",
                "value": href,
                "properties": {"title": title, "snippet": snippet}
            })
            
        return results

    def _scrape_duckduckgo_lite(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        results = []
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Referer": "https://lite.duckduckgo.com/",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
            "Origin": "https://lite.duckduckgo.com",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        url = "https://lite.duckduckgo.com/lite/"
        data = {'q': query}
        
        logger.info(f"Requesting DDG Lite: {url}")
        time.sleep(random.uniform(1.0, 2.0))
        response = requests.post(url, data=data, headers=headers, timeout=15)
        
        if response.status_code == 202:
            logger.warning("DuckDuckGo Lite returned 202. Inspecting content...")
            with open("ddg_lite_202.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
        if response.status_code != 200 and response.status_code != 202:
             raise OSINTToolError(f"DuckDuckGo Lite returned HTTP {response.status_code}")
             
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Lite structure: table -> tr -> td -> a.result-link
        links = soup.select("a.result-link")
        logger.info(f"Found {len(links)} DuckDuckGo Lite results")
        
        for link in links:
            if len(results) >= num_results:
                break
            
            href = link.get("href")
            if not href or "duckduckgo.com" in href:
                continue
                
            title = link.get_text(strip=True)
            
            # Snippet is usually in the next row or nearby text, hard to parse in Lite cleanly
            # but we can try to find the next td with class 'result-snippet'
            snippet = "No snippet available"
            parent_td = link.find_parent("td")
            if parent_td:
                parent_tr = parent_td.find_parent("tr")
                if parent_tr:
                    next_tr = parent_tr.find_next_sibling("tr")
                    if next_tr:
                        snippet_td = next_tr.select_one("td.result-snippet")
                        if snippet_td:
                            snippet = snippet_td.get_text(strip=True)

            results.append({
                "type": "url",
                "value": href,
                "properties": {"title": title, "snippet": snippet}
            })
            
        return results

    def _scrape_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        # 1. Try DuckDuckGo Library (most reliable)
        try:
            logger.info("Attempting DuckDuckGo search via library...")
            results = []
            with DDGS() as ddgs:
                ddg_gen = ddgs.text(query, max_results=num_results)
                if ddg_gen:
                    for r in ddg_gen:
                        results.append({
                            "type": "url",
                            "value": r.get('href'),
                            "properties": {
                                "title": r.get('title'),
                                "snippet": r.get('body')
                            }
                        })
            
            if results:
                logger.info(f"Found {len(results)} results via DuckDuckGo library")
                return results
                
        except Exception as e:
            logger.warning(f"DuckDuckGo library failed: {e}")

        # 2. Fallback to HTML Scraping
        try:
            logger.info("Falling back to DuckDuckGo (HTML)...")
            results = self._scrape_duckduckgo_html(query, num_results)
            if results:
                return results
        except Exception as e:
            logger.warning(f"DuckDuckGo (HTML) failed: {e}")

        # 3. Fallback to Lite Scraping
        try:
            logger.info("Falling back to DuckDuckGo (Lite)...")
            results = self._scrape_duckduckgo_lite(query, num_results)
            if results:
                return results
        except Exception as e:
            logger.warning(f"DuckDuckGo (Lite) failed: {e}")
            
        return []


def main():
    print("--- Starting Scraping Test ---")
    wrapper = GoogleSearchWrapper()
    
    # Test Query
    query = "site:stackoverflow.com python string formatting"
    print(f"Executing search for: {query}")
    
    try:
        start_time = time.time()
        result = wrapper.execute({"type": "query", "value": query}, num_results=5)
        end_time = time.time()
        
        print(f"\n--- Execution Completed in {end_time - start_time:.2f}s ---")
        print(f"Tool: {result['tool']}")
        print(f"Results Found: {len(result['results'])}")
        
        print("\n--- Results ---")
        for idx, item in enumerate(result['results']):
            print(f"{idx+1}. {item['value']}")
            print(f"   Title: {item['properties']['title']}")
            print(f"   Snippet: {item['properties']['snippet'][:100]}...")
            print("")
            
    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
