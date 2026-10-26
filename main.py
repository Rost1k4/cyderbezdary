"""Точка входу (кнопка Run): запускає сайт турніру через Streamlit.

Консольна версія (один матч у терміналі): python cli.py
"""
import subprocess
import sys
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    cmd = [sys.executable, "-m", "streamlit", "run", str(here / "app.py")] + sys.argv[1:]
    try:
        sys.exit(subprocess.call(cmd, cwd=here))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
