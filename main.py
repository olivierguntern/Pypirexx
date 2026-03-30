#!/usr/bin/env python3
"""
PyForex — Visualiseur graphique de paires Forex en chandeliers japonais.

Utilisation :
    python main.py

Dépendances :
    pip install -r requirements.txt
"""

import sys
import os

# Assure que le répertoire courant est dans le chemin Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from forex_app.main_window import ForexApp


def main():
    app = ForexApp()
    app.protocol("WM_DELETE_WINDOW", app.destroy)
    app.mainloop()


if __name__ == "__main__":
    main()
