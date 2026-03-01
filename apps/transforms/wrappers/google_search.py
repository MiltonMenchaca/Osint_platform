import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import logging
import random
import time
from .base import BaseWrapper, OSINTToolError

# Try importing DDGS, handle if missing
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

logger = logging.getLogger(__name__)

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
            
        # 2. Fallback to DuckDuckGo if Google failed or returned no results
        if not results:
            logger.info("Falling back to DuckDuckGo scraping...")
            try:
                results = self._scrape_duckduckgo(query, num_results)
            except Exception as e:
                logger.warning(f"DuckDuckGo scraping failed: {e}")

        # 3. Fallback to Yahoo if DuckDuckGo failed
        if not results:
            logger.info("Falling back to Yahoo scraping...")
            try:
                results = self._scrape_yahoo(query, num_results)
            except Exception as e:
                logger.warning(f"Yahoo scraping failed: {e}")

        execution_info = {
            "input_type": "query",
            "input_value": query,
            "execution_time": 0, # Placeholder
            "command": f"google_search '{query}'",
        }
        
        return self._format_output(results, execution_info)

    def _scrape_google(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        results = []
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
        
        # gbv=1 forces non-JS version (Google Basic Version)
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={num_results}&gbv=1"
        
        # Random delay
        time.sleep(random.uniform(2.0, 5.0))
        
        response = requests.get(url, headers=headers, timeout=15)
        
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
                response = requests.get(refresh_url, headers=headers, timeout=15)
                soup = BeautifulSoup(response.text, "html.parser")

        # Parse search results
        found_links = soup.select("a h3")
        logger.info(f"Found {len(found_links)} potential results (h3 inside a)")
        
        if not found_links:
            div_gs = soup.select("div.g")
            logger.info(f"Found {len(div_gs)} div.g elements")
            if not div_gs:
                 logger.warning("No Google search results found. HTML preview:")
                 logger.warning(soup.prettify()[:1000])
        
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

    def _scrape_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        # 1. Try DuckDuckGo Library (most reliable)
        if DDGS:
            try:
                logger.info("Attempting DuckDuckGo search via library...")
                results = []
                with DDGS() as ddgs:
                    # Retrieve all results at once to catch errors early
                    # Note: keywords is the argument name in some versions, but 'keywords' is positional
                    ddg_results = list(ddgs.text(keywords=query, max_results=num_results))
                    logger.info(f"DDGS returned {len(ddg_results)} results")
                    
                    for r in ddg_results:
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
        else:
            logger.warning("duckduckgo_search library not installed, skipping method")

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

    def _scrape_duckduckgo_html(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        results = []
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Referer": "https://duckduckgo.com/"
        }
        
        url = "https://html.duckduckgo.com/html/"
        data = {'q': query}
        
        # Random delay
        time.sleep(random.uniform(1.0, 3.0))
        
        response = requests.post(url, data=data, headers=headers, timeout=15)
        
        # Handle 202 specifically for DDG
        if response.status_code == 202:
             logger.warning("DuckDuckGo HTML returned 202 (Accepted/Processing), treating as no results for now")
             return []

        if response.status_code != 200:
             raise OSINTToolError(f"DuckDuckGo returned HTTP {response.status_code}")
             
        soup = BeautifulSoup(response.text, "html.parser")
        
        # DuckDuckGo HTML structure:
        # div.result -> h2.result__title -> a.result__a (link)
        #            -> a.result__snippet (snippet)
        
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
            
            if not href:
                continue
                
            snippet_tag = div.select_one("a.result__snippet")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            
            # Filter out ads or DDG internal links
            if "duckduckgo.com" in href:
                continue
                
            results.append({
                "type": "url",
                "value": href,
                "properties": {
                    "title": title,
                    "snippet": snippet
                }
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
            # We could save content for inspection but in prod just warn
            
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
            
            # Snippet logic for Lite
            snippet = "No snippet available"
            parent_td = link.find_parent("td")
            if parent_td:
                parent_tr = parent_td.find_parent("tr")
                if parent_tr:
                    next_tr = parent_tr.find_next_sibling("tr")
                    if next_tr:
                        snippet_td = next_tr.find("td", class_="result-snippet")
                        if snippet_td:
                            snippet = snippet_td.get_text(strip=True)
            
            results.append({
                "type": "url",
                "value": href,
                "properties": {
                    "title": title,
                    "snippet": snippet
                }
            })
            
        return results

    def _scrape_yahoo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        results = []
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Referer": "https://search.yahoo.com/"
        }
        
        url = "https://search.yahoo.com/search"
        params = {'p': query, 'n': num_results}
        
        logger.info(f"Requesting Yahoo: {url}")
        time.sleep(random.uniform(1.0, 3.0))
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
             raise OSINTToolError(f"Yahoo returned HTTP {response.status_code}")
             
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Yahoo structure: div.algo
        div_algos = soup.select("div.algo")
        logger.info(f"Found {len(div_algos)} Yahoo results")
        
        for div in div_algos:
            if len(results) >= num_results:
                break
                
            title_tag = div.select_one("h3.title > a")
            if not title_tag:
                title_tag = div.select_one("a")
                
            if not title_tag:
                continue
                
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")
            
            # Yahoo redirect URL cleaning
            # URL is often wrapped like https://r.search.yahoo.com/_ylt=.../RU=REAL_URL/...
            if href and "/RU=" in href:
                try:
                    href = href.split("/RU=")[1].split("/")[0]
                    href = urllib.parse.unquote(href)
                except:
                    pass
            
            if not href:
                continue
                
            snippet_tag = div.select_one("div.compText") or div.select_one("p.lh-16")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else "No snippet available"
            
            results.append({
                "type": "url",
                "value": href,
                "properties": {
                    "title": title,
                    "snippet": snippet
                }
            })
            
        return results
