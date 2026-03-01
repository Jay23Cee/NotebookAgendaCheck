from __future__ import annotations

import os

from notebookagendacheck.nicegui_app.main import run


def main() -> None:
    os.environ.setdefault("NACH_HOST", "127.0.0.1")
    os.environ.setdefault("NACH_PORT", "8080")
    run()


if __name__ == "__main__":
    main()

