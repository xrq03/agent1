from __future__ import annotations

import os
import subprocess
import sys


def main():
    cmd = [sys.executable, "-m", "streamlit", "run", "app/ui/streamlit_app.py"]
    subprocess.run(cmd, check=True, env=os.environ.copy())


if __name__ == "__main__":
    main()