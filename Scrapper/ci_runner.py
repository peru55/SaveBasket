"""CI runner which executes a small list of scrape jobs and pushes results to backend.

Designed for GitHub Actions but usable locally. Accepts a list of URLs or reads
`Scrapper/ci_jobs.txt` (one URL per line) when none provided.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import List

from dotenv import dotenv_values

from push_to_backend import build_payload_from_url, push_payload


DEFAULT_JOBS_FILE = os.path.join(os.path.dirname(__file__), 'ci_jobs.txt')
DEFAULT_BACKEND_ENV_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
)


def resolve_api_key(cli_key, environ=None, env_path=None):
    if cli_key:
        return cli_key

    environ = os.environ if environ is None else environ
    process_key = environ.get('SCRAPER_API_KEY')
    if process_key:
        return process_key

    env_path = DEFAULT_BACKEND_ENV_FILE if env_path is None else env_path
    if os.path.exists(env_path):
        file_key = dotenv_values(env_path).get('SCRAPER_API_KEY')
        if file_key:
            return file_key

    return None


def load_job_urls(file_path: str) -> List[str]:
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        print(f'Jobs file not found: {file_path}')
        return []
    with open(file_path, 'r', encoding='utf-8') as fh:
        return [line.strip() for line in fh if line.strip() and not line.strip().startswith('#')]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend')
    parser.add_argument('--key', required=False)
    parser.add_argument('--urls', required=False, default='')
    parser.add_argument('--jobs-file', default=DEFAULT_JOBS_FILE)
    parser.add_argument('--list-jobs', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)

    urls = []
    if args.urls:
        urls = [u.strip() for u in args.urls.splitlines() if u.strip()]
    if not urls:
        urls = load_job_urls(args.jobs_file)

    if not urls:
        print('No URLs to process; exiting.')
        return 0

    if args.list_jobs:
        print(f'Loaded {len(urls)} jobs from {os.path.abspath(args.jobs_file)}')
        for url in urls:
            print(url)
        return 0

    if not args.backend and not args.dry_run:
        parser.error('--backend is required unless --dry-run or --list-jobs is used')

    api_key = resolve_api_key(args.key, env_path=DEFAULT_BACKEND_ENV_FILE)
    if args.backend and not args.dry_run and not api_key:
        parser.error(
            'SCRAPER_API_KEY is required: pass --key, set the environment '
            'variable, or add it to backend/.env'
        )

    for url in urls:
        try:
            payload = build_payload_from_url(url)
        except Exception as exc:
            print(f'Failed to scrape {url}: {exc}')
            continue

        if args.dry_run:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            continue

        status, data = push_payload(args.backend, api_key, payload)
        print(f'Pushed {url}: status={status} response={data}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
