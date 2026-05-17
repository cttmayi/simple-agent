"""Search the web using DuckDuckGo."""

import html
import urllib.parse
from typing import Dict, Any, List
from simple_agent.tools.registry import get_global_registry, ToolDefinition


class WebSearch:
    """Search the web using DuckDuckGo Instant Answer API."""

    name = "web_search"
    description = "Search the web for information"

    @staticmethod
    def _search(query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search the web using DuckDuckGo Instant Answer API.

        Args:
            query: Search query
            max_results: Maximum number of results (default 10)

        Returns:
            Dict with success, results list, and optional error
        """
        try:
            # DuckDuckGo Instant Answer API (no API key required)
            # This provides basic search results
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=0"

            try:
                import urllib.request
                import json
            except ImportError:
                return {
                    "success": False,
                    "results": [],
                    "error": "Required modules not available"
                }

            try:
                # Make HTTP request
                req = urllib.request.Request(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; SimpleAgent/1.0)'
                    }
                )

                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "results": [],
                            "error": f"HTTP error: {response.status}"
                        }

                    data = json.loads(response.read().decode('utf-8'))
            except urllib.error.URLError as e:
                return {
                    "success": False,
                    "results": [],
                    "error": f"Network error: {e.reason}"
                }
            except TimeoutError:
                return {
                    "success": False,
                    "results": [],
                    "error": "Request timed out"
                }
            except Exception as e:
                return {
                    "success": False,
                    "results": [],
                    "error": f"Request failed: {str(e)}"
                }

            # Parse DuckDuckGo response
            results = []

            # Add abstract if available
            if data.get('Abstract'):
                results.append({
                    "title": data.get('Heading', query),
                    "url": data.get('AbstractURL', ''),
                    "snippet": html.unescape(data['Abstract'])
                })

            # Add related topics (these are actual search results)
            related_topics = data.get('RelatedTopics', [])
            for topic in related_topics:
                if len(results) >= max_results:
                    break

                # Topics can be either dicts or strings
                if isinstance(topic, dict):
                    if 'FirstURL' in topic and 'Text' in topic:
                        results.append({
                            "title": topic.get('FirstURL', '').split('/')[-1].replace('_', ' ').title(),
                            "url": topic['FirstURL'],
                            "snippet": html.unescape(topic['Text'])
                        })
                    elif 'Topics' in topic:  # Grouped topics
                        for subtopic in topic['Topics']:
                            if len(results) >= max_results:
                                break
                            if 'FirstURL' in subtopic and 'Text' in subtopic:
                                results.append({
                                    "title": subtopic.get('FirstURL', '').split('/')[-1].replace('_', ' ').title(),
                                    "url": subtopic['FirstURL'],
                                    "snippet": html.unescape(subtopic['Text'])
                                })

            # Ensure we don't return more than requested
            results = results[:max_results]

            # Build output string for CLI/Web display
            output_lines = []
            if results:
                output_lines.append(f"Found {len(results)} results:")
                for i, r in enumerate(results[:10], start=1):
                    output_lines.append(f"{i}. {r.get('title', '')}")
                    url = r.get('url', '')
                    if url:
                        output_lines.append(f"   URL: {url}")
                    snippet = r.get('snippet', '')
                    if snippet and len(snippet) < 150:
                        output_lines.append(f"   {snippet}")
                if len(results) > 10:
                    output_lines.append(f"... and {len(results) - 10} more results")
            else:
                output_lines.append("No results found")

            return {
                "success": True,
                "output": "\n".join(output_lines),  # For CLI/Web display
                "results": results,  # For AI
            }
        except Exception as e:
            return {
                "success": False,
                "results": [],
                "error": f"Search failed: {str(e)}"
            }

    @staticmethod
    def execute(query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search the web for information.

        Args:
            query: Search query
            max_results: Maximum number of results (default 10)

        Returns:
            Dict with success, results list, and optional error
        """
        return WebSearch._search(query, max_results)


# Auto-register with ToolRegistry
websearch_tool_def = ToolDefinition(
    name=WebSearch.name,
    description=WebSearch.description,
    fn=WebSearch.execute,
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default 10)"
            }
        },
        "required": ["query"]
    }
)

get_global_registry().register(websearch_tool_def)