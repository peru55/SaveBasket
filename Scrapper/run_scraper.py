import sys
from urllib.parse import urlparse
from scraper import EthicalScraper


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_scraper.py <url> [css_selector]")
        return
    url = sys.argv[1]
    selector = sys.argv[2] if len(sys.argv) > 2 else None

    s = EthicalScraper()
    try:
        html = s.fetch(url)
    except PermissionError as e:
        print("Permission error:", e)
        return
    except Exception as e:
        print("Error fetching URL:", e)
        return

    # Try site-specific parsing first
    result = s.parse_site(url, html)
    if result and result.get("price") is not None:
        print("Parsed result:", result)
    elif result and result.get("error"):
        print("Parse error:", result["error"])
        if result.get("title"):
            print("Partial result:", result)
    elif selector:
        prices = s.parse_prices(html, selector)
        print("Found prices:", prices)
    else:
        prices = s.parse_prices(html, selector)
        print("Parsed result:", result)
        print("Found prices:", prices)


if __name__ == "__main__":
    main()
