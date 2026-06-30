from __future__ import annotations

import httpx

from luminesk.core.registry import registry
from luminesk.utils.downloads import get_latest_download_url


def main() -> int:
    exit_code = 0

    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for core in registry.get_all():
            try:
                url = get_latest_download_url(core, client=client)
            except Exception as exc:
                exit_code = 1
                print(f"{core.id}: ERROR: {exc}")
                continue

            print(f"{core.id}: {url}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
