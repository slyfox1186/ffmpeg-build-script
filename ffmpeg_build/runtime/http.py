"""HTTP client identity, including upstream compatibility exceptions."""

from urllib.parse import urlsplit

HTTP_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)


def user_agent_arguments(url: str, *, git: bool = False) -> list[str]:
    """Keep VideoLAN's GitLab on the client's native user agent.

    code.videolan.org rejects the browser identity with HTTP 418 for both
    Git requests and source archives. Other hosts retain the project identity.
    """
    if urlsplit(url).hostname == "code.videolan.org":
        return []
    return ["-c", f"http.userAgent={HTTP_USER_AGENT}"] if git else ["--user-agent", HTTP_USER_AGENT]
