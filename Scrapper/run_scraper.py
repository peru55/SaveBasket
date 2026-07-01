import argparse
import json
import logging
import sys

from json_store import DEFAULT_STORE_ROOT, persist_product
from push_to_backend import push_payload
from scraper import EthicalScraper


logger = logging.getLogger("scraper_runner")


def main():
    parser = argparse.ArgumentParser(description="Scrape a supermarket product page and optionally persist JSON snapshots.")
    parser.add_argument("url", help="Product page URL to scrape")
    parser.add_argument("selector", nargs="?", help="Optional CSS selector for raw price extraction")
    parser.add_argument("--json-dir", default=str(DEFAULT_STORE_ROOT), help="Directory used to store product JSON files")
    parser.add_argument("--backend", help="Backend base URL. If set, push newly scraped or changed products to the API")
    parser.add_argument("--key", help="Optional X-SCRAPER-KEY value for backend ingestion")
    parser.add_argument("--branch-name", default="Website", help="Branch name to send to the backend")
    parser.add_argument("--branch-city", default="Nairobi", help="Branch city to send to the backend")
    parser.add_argument("--source", help="Override the supermarket source name sent to the backend")
    parser.add_argument("--no-json", action="store_true", help="Disable JSON persistence")
    parser.add_argument("--push-unchanged", action="store_true", help="Push to the backend even when the local JSON snapshot is unchanged")
    args = parser.parse_args()

    url = args.url
    selector = args.selector

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
        product_name = result.get("name") or result.get("title")
        print("Parsed result:", result)
        if not args.no_json:
            persist_result = persist_product(result, root_dir=args.json_dir)
            if persist_result.status == "created":
                print(f"JSON created: {persist_result.path}")
                logger.info("JSON created for %s", product_name)
            elif persist_result.status == "updated":
                print(
                    f"JSON updated: {persist_result.path} (price {persist_result.previous_price} -> {persist_result.current_price})"
                )
                logger.info(
                    "Price change detected for %s: %s -> %s",
                    product_name,
                    persist_result.previous_price,
                    persist_result.current_price,
                )
            else:
                print(f"JSON unchanged: skipped {persist_result.path}")
                logger.info("Unchanged product skipped for %s", product_name)

            should_push = bool(args.backend) and (persist_result.changed or args.push_unchanged)
            if should_push:
                payload = {
                    "source": args.source or result.get("source") or "Unknown",
                    "branch": {"name": args.branch_name, "city": args.branch_city},
                    "products": [result],
                }
                push_reason = "changed" if persist_result.changed else "unchanged"
                logger.info("Pushing %s product to backend: %s", push_reason, product_name)
                status, data = push_payload(args.backend, args.key, payload)
                print(f"Backend responded: {status}")
                if 200 <= status < 300:
                    print(f"Successfully pushed to backend: {product_name}")
                    logger.info("Successfully pushed to backend: %s", product_name)
                else:
                    print(f"Failed to push to backend: {product_name}")
                    logger.error("Failed to push to backend: %s (status=%s)", product_name, status)
                print(json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, (dict, list)) else data)
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
