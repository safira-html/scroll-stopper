"""Ponto de entrada de `ss prepare-presenter` (o bin/ss troca o hifen por sublinhado); o codigo mora em presenter.py."""
import sys

from ss_lib.presenter import main

if __name__ == "__main__":
    sys.exit(main())
