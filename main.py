#!/usr/bin/env python3
"""
PyForex — Visualiseur graphique de paires Forex en chandeliers japonais.

Utilisation directe :
    python main.py

Via pip (après installation) :
    pip install pyforex
    pyforex

Dépendances (sans pip install) :
    pip install -r requirements.txt
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from forex_app.__main__ import main

if __name__ == "__main__":
    main()
