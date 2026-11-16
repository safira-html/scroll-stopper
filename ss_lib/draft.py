"""Ponto de entrada de `ss draft` (a logica fica em ss_lib.render)."""
import sys

from ss_lib.render import main_draft

if __name__ == "__main__":
    sys.exit(main_draft())
