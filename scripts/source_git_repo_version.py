#!/usr/bin/env python3

import argparse
import logging
import re
import sys
import time
from html import unescape
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[90m",
        "INFO": "\033[94m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m",
    }
    SYMBOLS = {
        "DEBUG": "  ",
        "INFO": "->",
        "WARNING": "!!",
        "ERROR": "XX",
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        symbol = self.SYMBOLS.get(record.levelname, "  ")
        reset = self.COLORS["RESET"]
        return f"{color}{symbol} {record.getMessage()}{reset}"


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

TAG_HREF_RE = re.compile(r'href="[^"]*?/(?:releases/)?tag/([^"#?]+)"')
GENERIC_VERSION_RE = re.compile(
    r"(?:[a-zA-Z][-a-zA-Z0-9]*-)?[vVnN]?([0-9]+(?:[._-][0-9]+){1,3}(?:[-_.]?[a-zA-Z][a-zA-Z0-9]*)?)"
)
TRIM_RE = re.compile(r"^[-._]+|[-._]+$")
EXCLUDE_WORDS_RE = re.compile(
    r"(alpha|beta|dev|early|init|m[0-9]+|next|pending|pre|preview|snapshot|nightly|canary|test|experimental|tentative|unstable|wip|draft"
    r"|a[0-9]+|b[0-9]+|c[0-9]+|rc[0-9]*)",
    re.IGNORECASE,
)
MAX_ATTEMPTS = 3
INITIAL_RETRY_INTERVAL = 2
BACKOFF_FACTOR = 2
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def create_http_session():
    return build_opener()


def get_html_content(opener, url):
    interval = INITIAL_RETRY_INTERVAL

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            request = Request(url, headers=DEFAULT_HEADERS)
            with opener.open(request, timeout=15) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except HTTPError as exc:
            if exc.code in RETRY_STATUS_CODES and attempt < MAX_ATTEMPTS:
                logging.warning(f"Failed: {url} (HTTPError {exc.code}), retrying in {interval}s...")
                time.sleep(interval)
                interval *= BACKOFF_FACTOR
                continue
            logging.warning(f"Failed: {url} (HTTPError {exc.code})")
            return None
        except (URLError, OSError) as exc:
            if attempt < MAX_ATTEMPTS:
                logging.warning(f"Failed: {url} ({exc.__class__.__name__}), retrying in {interval}s...")
                time.sleep(interval)
                interval *= BACKOFF_FACTOR
                continue
            logging.warning(f"Failed: {url} ({exc.__class__.__name__})")
            return None

    return None


def natural_version_key(version: str):
    parts = []
    for token in re.findall(r"\d+|[A-Za-z]+", version):
        if token.isdigit():
            parts.append((0, int(token)))
        else:
            parts.append((1, token.lower()))
    return parts


def unique_preserving_order(values: Iterable[str]):
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        yield value


def collect_tag_names(html_content: str):
    return list(unique_preserving_order(unescape(match) for match in TAG_HREF_RE.findall(html_content)))


def parse_latest_version(html_content, prefix="", exclude_pattern="", version_regex="", index=1):
    tag_names = collect_tag_names(html_content)
    if not tag_names:
        logging.debug("No tag links found in HTML")
        return None

    logging.debug(f"Tags found: {tag_names[:10]}{'...' if len(tag_names) > 10 else ''}")

    exclude_re = re.compile(exclude_pattern) if exclude_pattern else None
    version_filter_re = re.compile(version_regex) if version_regex else None
    versions = []

    for tag_name in tag_names:
        if exclude_re and exclude_re.search(tag_name):
            continue

        candidate = tag_name
        if prefix:
            if not candidate.startswith(prefix):
                continue
            candidate = candidate[len(prefix):]
        else:
            match = GENERIC_VERSION_RE.search(candidate)
            if not match:
                continue
            candidate = match.group(1)

        candidate = TRIM_RE.sub("", candidate)
        if not candidate or EXCLUDE_WORDS_RE.search(candidate):
            continue
        if version_filter_re and not version_filter_re.fullmatch(candidate):
            continue
        versions.append(candidate)

    versions = list(unique_preserving_order(versions))
    logging.debug(f"Valid versions: {versions[:10]}{'...' if len(versions) > 10 else ''}")
    if not versions:
        return None

    sorted_versions = sorted(versions, key=natural_version_key, reverse=True)
    chosen_index = max(index - 1, 0)
    if chosen_index >= len(sorted_versions):
        return None
    return sorted_versions[chosen_index]


def fetch_paths(base_url, url_type):
    if url_type == "tags":
        return [f"{base_url}/tags"]
    if url_type == "releases":
        return [f"{base_url}/releases"]
    return [base_url, f"{base_url}/releases", f"{base_url}/tags"]


def get_latest_release_version(opener, url, prefix="", exclude_pattern="", version_regex="", index=1, url_type="auto"):
    base_url = url.rstrip("/")
    html_content = ""

    for sub_url in fetch_paths(base_url, url_type):
        path = sub_url.replace(base_url, "") or "/"
        logging.info(f"Fetching {path}")
        sub_html = get_html_content(opener, sub_url)
        if sub_html:
            html_content += sub_html

    return parse_latest_version(
        html_content,
        prefix=prefix,
        exclude_pattern=exclude_pattern,
        version_regex=version_regex,
        index=index,
    )


def retry_version_fetch(opener, url, prefix="", exclude_pattern="", version_regex="", index=1, url_type="auto"):
    interval = INITIAL_RETRY_INTERVAL
    repo_name = url.rstrip("/").split("/")[-1]

    logging.info(f"Checking {repo_name} ({url})")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            logging.info(f"Retry {attempt}/{MAX_ATTEMPTS}")

        version = get_latest_release_version(
            opener,
            url,
            prefix=prefix,
            exclude_pattern=exclude_pattern,
            version_regex=version_regex,
            index=index,
            url_type=url_type,
        )
        if version:
            logging.info(f"Found: {version}")
            return version

        if attempt < MAX_ATTEMPTS:
            logging.warning(f"No version found, retrying in {interval}s...")
            time.sleep(interval)
            interval *= BACKOFF_FACTOR

    logging.error("Failed to fetch version after all attempts")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch the latest release or tag version from a GitHub repository page."
    )
    parser.add_argument("url", nargs="?", default=None, help="GitHub repository URL")
    parser.add_argument("-u", "--url", dest="url_flag", help="GitHub repository URL")
    parser.add_argument("--prefix", default="", help="Required tag prefix, such as v or n")
    parser.add_argument("--exclude-pattern", default="", help="Regex to exclude matching tag names")
    parser.add_argument("--version-regex", default="", help="Regex that the normalized version must fully match")
    parser.add_argument("--index", type=int, default=1, help="Sorted match index to return")
    parser.add_argument("--url-type", choices=["auto", "tags", "releases"], default="auto")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--version-only", action="store_true")
    args = parser.parse_args()

    repo_url = args.url_flag or args.url
    if not repo_url:
        parser.error("a URL is required (positional or via -u/--url)")

    if args.version_only or args.quiet:
        logging.disable(logging.CRITICAL)
    else:
        setup_logging(verbose=args.verbose)

    session = create_http_session()
    version = retry_version_fetch(
        session,
        repo_url,
        prefix=args.prefix,
        exclude_pattern=args.exclude_pattern,
        version_regex=args.version_regex,
        index=args.index,
        url_type=args.url_type,
    )

    if version:
        print(version)
    else:
        sys.exit(1)
