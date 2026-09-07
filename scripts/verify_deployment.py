"""Verify a deployed AI Quiz instance without requiring third-party tooling."""

import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def fetch(url):
    with urlopen(url, timeout=30) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def main():
    base_url = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")
    checks = [("health", f"{base_url}/health"), ("login", f"{base_url}/login")]
    failed = False
    for name, url in checks:
        try:
            status, body = fetch(url)
            expected = '"status"' in body if name == "health" else "QuizGen AI" in body
            result = "PASS" if status == 200 and expected else "FAIL"
            print(f"{result} {name}: HTTP {status}")
            failed = failed or result == "FAIL"
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"FAIL {name}: {exc}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
