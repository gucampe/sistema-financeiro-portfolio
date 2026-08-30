#!/usr/bin/env python3
"""Regenera os screenshots da Ajuda em static/img/ajuda/.

Uso (a partir da raiz do projeto):

  source .venv/bin/activate
  python scripts/ajuda/screenshots_ajuda.py

Ou o alvo do Makefile:

  make ajuda-screenshots
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "e2e/specs/ajuda/test_gerar_screenshots.py",
        "--browser",
        "chromium",
        "-s",
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
