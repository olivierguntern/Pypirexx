"""
Point d'entrée pour :
  - la commande CLI : pyforex
  - l'exécution en module : python -m forex_app
"""


def main():
    """Lance l'application PyForex."""
    from forex_app.main_window import ForexApp

    app = ForexApp()
    app.protocol("WM_DELETE_WINDOW", app.destroy)
    app.mainloop()


if __name__ == "__main__":
    main()
