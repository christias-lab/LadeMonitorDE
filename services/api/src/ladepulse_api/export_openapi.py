from __future__ import annotations

import json
from pathlib import Path

from ladepulse_api.main import app


def main() -> None:
    target = Path("packages/contracts/openapi/openapi.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(target)


if __name__ == "__main__":
    main()
