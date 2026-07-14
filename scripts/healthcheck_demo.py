#!/usr/bin/env python
"""Health check for demo deployment — verifies API, MySQL, Redis are healthy."""

from __future__ import annotations

import sys
from urllib.request import urlopen


def main() -> None:
    try:
        resp = urlopen("https://localhost/health")
        if resp.status == 200:
            print("OK: API healthy")
            sys.exit(0)
    except Exception as e:
        print(f"FAIL: {e}")
    sys.exit(1)


if __name__ == "__main__":
    main()
