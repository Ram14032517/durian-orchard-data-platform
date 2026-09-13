"""Report staged file names containing exact known private values, never values."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def staged_names() -> list[str]:
    output = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True
    )
    return output.splitlines()


def private_values() -> list[str]:
    values: list[str] = []
    for relative in (
        "receiver_gateway/tuya_cloud_secret.h",
        "receiver_gateway/tuya_local_secret.h",
        "receiver_gateway/farm_secret.h",
        "wifi_range_test/wifi_secret.h",
    ):
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        values.extend(re.findall(r'"([^"\r\n]{8,})"', text))
    return list(dict.fromkeys(values))


def main() -> None:
    values = private_values()
    hits: list[str] = []
    for name in staged_names():
        blob = subprocess.check_output(["git", "show", f":{name}"], cwd=ROOT)
        if any(value.encode("utf-8") in blob for value in values):
            hits.append(name)
    print("\n".join(hits) if hits else "No exact private-value matches in staged files.")


if __name__ == "__main__":
    main()
