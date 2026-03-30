"""Fenêtre principale PyForex — mise en page, panneau de contrôle, gestion des données."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime, timezone

from forex_app.config import FOREX_PAIRS, TIMEFRAMES, THEME
from forex_app.data_fetcher import fetch_ohlcv, resample_4h
from forex_app.chart_widget import ChartWidget


# ---------------------------------------------------------------------------
# Helpers UI
# ---------------------------------------------------------------------------

def _label(parent, text, font=("Helvetica", 9), fg=None, **kw):
    return tk.Label(
        parent, text=text,
        bg=THEME["bg_secondary"],
        fg=fg or THEME["text"],
        font=font,
        **kw,
    )


def _section_header(parent, text):
    frame = tk.Frame(parent, bg=THEME["bg_panel"])
    frame.pack(fill=tk.X)
    tk.Label(
        frame, text=text,
        bg=THEME["bg_panel"],
        fg=THEME["accent"],
        font=("Helvetica", 8, "bold"),
        anchor="w", padx=10, pady=5,
    ).pack(fill=tk.X)
    return frame


# ---------------------------------------------------------------------------
# Fenêtre principale
# ---------------------------------------------------------------------------

class ForexApp(tk.Tk):
    """Application principale PyForex."""

    SIDEBAR_WIDTH = 230

    def __init__(self):
        super().__init__()

        self.title("PyForex  —  Graphiques Forex en Chandeliers Japonais")
        self.geometry("1440x900")
        self.minsize(1000, 680)
        self.configure(bg=THEME["bg"])

        # ── État ──────────────────────────────────────────────────────
        self._current_ticker = "EURUSD=X"
        self._current_name   = "EUR/USD"
        self._timeframe      = tk.StringVar(value="1 jour")
        self._auto_refresh   = tk.BooleanVar(value=False)
        self._refresh_sec    = tk.IntVar(value=60)

        # Indicateurs activés
        self._ind = {
            "sma20":    tk.BooleanVar(value=True),
            "sma50":    tk.BooleanVar(value=False),
            "ema20":    tk.BooleanVar(value=False),
            "bollinger": tk.BooleanVar(value=False),
            "rsi":      tk.BooleanVar(value=False),
            "macd":     tk.BooleanVar(value=False),
        }

        # Infos dernière bougie
        self._info = {k: tk.StringVar(value="—") for k in
                      ["paire", "prix", "variation", "volume", "haut", "bas", "ouverture"]}

        self._stop_refresh  = False
        self._refresh_thread: threading.Thread | None = None
        self._loading       = False

        # ── Construction ──────────────────────────────────────────────
        self._build_ui()
        self._apply_ttk_style()

        # Chargement initial légèrement différé
        self.after(400, self.load_data)

    # ==================================================================
    # Construction de l'interface
    # ==================================================================

    def _build_ui(self):
        self._build_header()

        # Conteneur principal
        body = tk.Frame(self, bg=THEME["bg"])
        body.pack(fill=tk.BOTH, expand=True)

        # Barre latérale gauche
        sidebar = tk.Frame(body, bg=THEME["bg_secondary"],
                           width=self.SIDEBAR_WIDTH)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Zone graphique droite
        chart_area = tk.Frame(body, bg=THEME["bg"])
        chart_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.chart = ChartWidget(chart_area)
        self.chart.pack(fill=tk.BOTH, expand=True)
        self.chart.on_cursor_move = self._on_cursor_move

        self._build_statusbar()

    # ------------------------------------------------------------------
    # En-tête
    # ------------------------------------------------------------------

    def _build_header(self):
        header = tk.Frame(self, bg=THEME["bg_panel"], height=52)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Logo
        logo_frame = tk.Frame(header, bg=THEME["bg_panel"])
        logo_frame.pack(side=tk.LEFT, padx=16, pady=8)
        tk.Label(logo_frame, text="Py",    font=("Helvetica", 22, "bold"),
                 bg=THEME["bg_panel"], fg=THEME["accent"]).pack(side=tk.LEFT)
        tk.Label(logo_frame, text="Forex", font=("Helvetica", 22, "bold"),
                 bg=THEME["bg_panel"], fg=THEME["text"]).pack(side=tk.LEFT)

        tk.Label(header, text="Visualiseur de chandeliers japonais",
                 bg=THEME["bg_panel"], fg=THEME["text_secondary"],
                 font=("Helvetica", 9)).pack(side=tk.LEFT, padx=8)

        # Affichage prix courant dans l'en-tête
        self._header_price_var = tk.StringVar(value="")
        self._header_price_lbl = tk.Label(
            header, textvariable=self._header_price_var,
            bg=THEME["bg_panel"], fg=THEME["text"],
            font=("Courier", 14, "bold"),
        )
        self._header_price_lbl.pack(side=tk.RIGHT, padx=20)

        # Horloge UTC
        self._clock_var = tk.StringVar()
        tk.Label(header, textvariable=self._clock_var,
                 bg=THEME["bg_panel"], fg=THEME["text_secondary"],
                 font=("Courier", 9)).pack(side=tk.RIGHT, padx=12)
        self._tick_clock()

    def _tick_clock(self):
        now = datetime.now(timezone.utc).strftime("UTC  %Y-%m-%d  %H:%M:%S")
        self._clock_var.set(now)
        self.after(1000, self._tick_clock)

    # ------------------------------------------------------------------
    # Barre latérale
    # ------------------------------------------------------------------

    def _build_sidebar(self, parent):
        # Canvas + Scrollbar pour sidebar scrollable
        canvas = tk.Canvas(parent, bg=THEME["bg_secondary"],
                           highlightthickness=0, width=self.SIDEBAR_WIDTH - 2)
        vsb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)

        frame = tk.Frame(canvas, bg=THEME["bg_secondary"])
        frame.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel
        def _scroll(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _scroll)

        self._build_sidebar_content(frame)

    def _build_sidebar_content(self, parent):
        pad = {"padx": 10, "pady": 3}

        # ── Paires Forex ───────────────────────────────────────────────
        _section_header(parent, "  PAIRES FOREX")

        list_frame = tk.Frame(parent, bg=THEME["bg_secondary"])
        list_frame.pack(fill=tk.X, padx=6, pady=4)

        self._pairs_lb = tk.Listbox(
            list_frame,
            bg=THEME["bg"],
            fg=THEME["text"],
            selectbackground=THEME["bg_panel"],
            selectforeground=THEME["accent"],
            font=("Courier", 9),
            height=16,
            borderwidth=0,
            highlightthickness=1,
            highlightcolor=THEME["border"],
            highlightbackground=THEME["border"],
            activestyle="none",
        )
        lb_scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                 command=self._pairs_lb.yview)
        self._pairs_lb.configure(yscrollcommand=lb_scroll.set)
        self._pairs_lb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lb_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._pairs_map: dict[str, tuple[str, str]] = {}
        self._header_indices: set[int] = set()
        self._populate_pairs()
        self._pairs_lb.bind("<<ListboxSelect>>", self._on_pair_selected)

        # Recherche rapide
        search_frame = tk.Frame(parent, bg=THEME["bg_secondary"])
        search_frame.pack(fill=tk.X, **pad)
        _label(search_frame, "Recherche :").pack(anchor="w")

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        search_entry = tk.Entry(
            search_frame, textvariable=self._search_var,
            bg=THEME["bg_panel"], fg=THEME["text"],
            insertbackground=THEME["text"],
            font=("Courier", 9), borderwidth=0,
            highlightthickness=1,
            highlightcolor=THEME["accent"],
            highlightbackground=THEME["border"],
        )
        search_entry.pack(fill=tk.X, pady=(2, 0))

        # ── Unité de temps ─────────────────────────────────────────────
        _section_header(parent, "  UNITÉ DE TEMPS")

        tf_frame = tk.Frame(parent, bg=THEME["bg_secondary"])
        tf_frame.pack(fill=tk.X, **pad)

        self._tf_combo = ttk.Combobox(
            tf_frame,
            values=list(TIMEFRAMES.keys()),
            textvariable=self._timeframe,
            state="readonly",
            font=("Helvetica", 9),
        )
        self._tf_combo.pack(fill=tk.X)
        self._tf_combo.bind("<<ComboboxSelected>>", lambda _: self.load_data())

        # ── Indicateurs ────────────────────────────────────────────────
        _section_header(parent, "  INDICATEURS TECHNIQUES")

        ind_frame = tk.Frame(parent, bg=THEME["bg_secondary"])
        ind_frame.pack(fill=tk.X, **pad)

        ind_defs = [
            ("SMA 20",            "sma20",    "#f0b429"),
            ("SMA 50",            "sma50",    "#ff7b72"),
            ("EMA 20",            "ema20",    "#79c0ff"),
            ("Bandes de Bollinger","bollinger","#d2a8ff"),
            ("RSI (14)",          "rsi",      "#e94560"),
            ("MACD (12/26/9)",    "macd",     "#f0b429"),
        ]
        for label, key, color in ind_defs:
            cb = tk.Checkbutton(
                ind_frame,
                text=f"  {label}",
                variable=self._ind[key],
                bg=THEME["bg_secondary"],
                fg=color,
                selectcolor=THEME["bg"],
                activebackground=THEME["bg_secondary"],
                activeforeground=color,
                font=("Helvetica", 9),
                anchor="w",
                cursor="hand2",
                command=self.load_data,
            )
            cb.pack(fill=tk.X, pady=1)

        # ── Auto-rafraîchissement ──────────────────────────────────────
        _section_header(parent, "  AUTO-RAFRAÎCHISSEMENT")

        ar_frame = tk.Frame(parent, bg=THEME["bg_secondary"])
        ar_frame.pack(fill=tk.X, **pad)

        tk.Checkbutton(
            ar_frame,
            text="  Activer",
            variable=self._auto_refresh,
            bg=THEME["bg_secondary"],
            fg=THEME["text"],
            selectcolor=THEME["bg"],
            activebackground=THEME["bg_secondary"],
            activeforeground=THEME["text"],
            font=("Helvetica", 9),
            anchor="w",
            cursor="hand2",
            command=self._toggle_auto_refresh,
        ).pack(fill=tk.X)

        _label(ar_frame, "Intervalle :").pack(anchor="w", pady=(6, 2))

        iv_frame = tk.Frame(ar_frame, bg=THEME["bg_secondary"])
        iv_frame.pack(fill=tk.X)
        for secs, label in [(30, "30s"), (60, "1m"), (120, "2m"),
                             (300, "5m"), (600, "10m")]:
            tk.Radiobutton(
                iv_frame, text=label, value=secs,
                variable=self._refresh_sec,
                bg=THEME["bg_secondary"], fg=THEME["text_secondary"],
                selectcolor=THEME["bg"],
                activebackground=THEME["bg_secondary"],
                font=("Helvetica", 8),
            ).pack(side=tk.LEFT)

        # ── Bouton Actualiser ──────────────────────────────────────────
        _section_header(parent, "")

        btn_frame = tk.Frame(parent, bg=THEME["bg_secondary"])
        btn_frame.pack(fill=tk.X, padx=10, pady=8)

        self._refresh_btn = tk.Button(
            btn_frame,
            text="↻   Actualiser",
            command=self.load_data,
            bg=THEME["accent"],
            fg="#ffffff",
            activebackground=THEME["accent_dark"],
            activeforeground="#ffffff",
            font=("Helvetica", 10, "bold"),
            borderwidth=0,
            cursor="hand2",
            pady=8,
            relief="flat",
        )
        self._refresh_btn.pack(fill=tk.X)

        # ── Informations dernière bougie ───────────────────────────────
        _section_header(parent, "  DERNIÈRE BOUGIE")

        info_frame = tk.Frame(parent, bg=THEME["bg_secondary"])
        info_frame.pack(fill=tk.X, padx=10, pady=4)

        info_rows = [
            ("Paire",       "paire"),
            ("Prix",        "prix"),
            ("Variation",   "variation"),
            ("Haut",        "haut"),
            ("Bas",         "bas"),
            ("Ouverture",   "ouverture"),
            ("Volume",      "volume"),
        ]
        self._variation_lbl: tk.Label | None = None

        for label, key in info_rows:
            row = tk.Frame(info_frame, bg=THEME["bg_secondary"])
            row.pack(fill=tk.X, pady=1)
            _label(row, f"{label} :", font=("Helvetica", 8),
                   fg=THEME["text_secondary"]).pack(side=tk.LEFT)
            lbl = tk.Label(
                row,
                textvariable=self._info[key],
                bg=THEME["bg_secondary"],
                fg=THEME["text"],
                font=("Courier", 8),
                anchor="e",
            )
            lbl.pack(side=tk.RIGHT)
            if key == "variation":
                self._variation_lbl = lbl

        # ── Curseur (affiché au survol) ────────────────────────────────
        _section_header(parent, "  CURSEUR")

        cur_frame = tk.Frame(parent, bg=THEME["bg_secondary"])
        cur_frame.pack(fill=tk.X, padx=10, pady=4)

        self._cursor_price_var = tk.StringVar(value="—")
        self._cursor_date_var  = tk.StringVar(value="—")

        for label, var in [("Prix :", self._cursor_price_var),
                            ("Date :", self._cursor_date_var)]:
            row = tk.Frame(cur_frame, bg=THEME["bg_secondary"])
            row.pack(fill=tk.X, pady=1)
            _label(row, label, font=("Helvetica", 8),
                   fg=THEME["text_secondary"]).pack(side=tk.LEFT)
            tk.Label(row, textvariable=var,
                     bg=THEME["bg_secondary"], fg=THEME["blue"],
                     font=("Courier", 8), anchor="e").pack(side=tk.RIGHT)

        # Espace en bas
        tk.Frame(parent, bg=THEME["bg_secondary"], height=20).pack()

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=THEME["bg_panel"], height=28)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self._status_var  = tk.StringVar(value="Prêt")
        self._loading_var = tk.StringVar(value="")

        tk.Label(bar, textvariable=self._status_var,
                 bg=THEME["bg_panel"], fg=THEME["text_secondary"],
                 font=("Helvetica", 8), anchor="w").pack(
                     side=tk.LEFT, padx=10, fill=tk.Y)

        tk.Label(bar, textvariable=self._loading_var,
                 bg=THEME["bg_panel"], fg=THEME["yellow"],
                 font=("Helvetica", 8), anchor="e").pack(
                     side=tk.RIGHT, padx=10, fill=tk.Y)

    # ------------------------------------------------------------------
    # Peuplement des paires
    # ------------------------------------------------------------------

    def _populate_pairs(self, filter_str: str = ""):
        """Remplit la listbox avec les paires (optionnellement filtrées)."""
        self._pairs_lb.delete(0, tk.END)
        self._pairs_map.clear()
        self._header_indices.clear()

        filt = filter_str.upper()

        for category, pairs in FOREX_PAIRS.items():
            visible = [(d, t) for d, t in pairs
                       if not filt or filt in d.upper()]
            if not visible:
                continue

            # En-tête de catégorie
            idx = self._pairs_lb.size()
            self._pairs_lb.insert(tk.END, f"  ── {category} ──")
            self._pairs_lb.itemconfig(
                idx,
                fg=THEME["text_secondary"],
                selectbackground=THEME["bg_secondary"],
                selectforeground=THEME["text_secondary"],
            )
            self._header_indices.add(idx)

            for display, ticker in visible:
                entry = f"  {display}"
                idx = self._pairs_lb.size()
                self._pairs_lb.insert(tk.END, entry)
                self._pairs_map[idx] = (display, ticker)

                # Surligner la paire active
                if ticker == self._current_ticker:
                    self._pairs_lb.selection_set(idx)
                    self._pairs_lb.see(idx)

    def _on_search(self, *_):
        self._populate_pairs(self._search_var.get())

    # ------------------------------------------------------------------
    # Sélection de paire
    # ------------------------------------------------------------------

    def _on_pair_selected(self, _event):
        sel = self._pairs_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx in self._header_indices:
            self._pairs_lb.selection_clear(0, tk.END)
            return
        if idx not in self._pairs_map:
            return
        display, ticker = self._pairs_map[idx]
        self._current_ticker = ticker
        self._current_name   = display
        self._info["paire"].set(display)
        self.load_data()

    # ------------------------------------------------------------------
    # Chargement des données
    # ------------------------------------------------------------------

    def load_data(self):
        """Lance le chargement des données dans un thread secondaire."""
        if self._loading:
            return

        self._loading = True
        self._status_var.set(f"Chargement de {self._current_name} …")
        self._loading_var.set("⟳ Chargement…")
        self._refresh_btn.config(state=tk.DISABLED)

        ticker      = self._current_ticker
        name        = self._current_name
        tf_name     = self._timeframe.get()
        indicators  = {k: v.get() for k, v in self._ind.items()}

        def _worker():
            try:
                period, interval = TIMEFRAMES[tf_name]
                if tf_name == "4 heures":
                    df = fetch_ohlcv(ticker, period, "1h")
                    if not df.empty:
                        df = resample_4h(df)
                else:
                    df = fetch_ohlcv(ticker, period, interval)
                self.after(0, lambda: self._on_data_ready(df, name, indicators))
            except Exception as exc:
                self.after(0, lambda: self._on_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_data_ready(self, df: "pd.DataFrame", name: str, indicators: dict):
        self._loading = False
        self._refresh_btn.config(state=tk.NORMAL)
        self._loading_var.set("")

        if df is None or df.empty:
            self._status_var.set("Aucune donnée reçue.")
            return

        # Mise à jour du panneau d'informations
        last   = df.iloc[-1]
        first  = df.iloc[0]
        change = (last["Close"] - first["Close"]) / first["Close"] * 100

        self._info["prix"].set(f"{last['Close']:.5f}")
        self._info["haut"].set(f"{last['High']:.5f}")
        self._info["bas"].set(f"{last['Low']:.5f}")
        self._info["ouverture"].set(f"{last['Open']:.5f}")

        vol = last["Volume"]
        self._info["volume"].set(
            f"{vol:,.0f}" if vol > 0 else "N/A"
        )

        chg_str = f"{change:+.2f}%"
        self._info["variation"].set(chg_str)
        if self._variation_lbl:
            color = THEME["green"] if change >= 0 else THEME["red"]
            self._variation_lbl.config(fg=color)

        # Prix dans l'en-tête
        self._header_price_var.set(f"{name}   {last['Close']:.5f}")
        color_h = THEME["green"] if change >= 0 else THEME["red"]
        self._header_price_lbl.config(fg=color_h)

        # Rendu du graphique
        self.chart.update_chart(df, name, indicators)

        ts = datetime.now().strftime("%H:%M:%S")
        self._status_var.set(
            f"{name}  ·  {len(df)} bougies  ·  {self._timeframe.get()}  ·  {ts}"
        )

    def _on_error(self, msg: str):
        self._loading = False
        self._refresh_btn.config(state=tk.NORMAL)
        self._loading_var.set("")
        self._status_var.set(f"Erreur : {msg}")
        messagebox.showerror("Erreur de chargement", msg, parent=self)

    # ------------------------------------------------------------------
    # Callback crosshair
    # ------------------------------------------------------------------

    def _on_cursor_move(self, price: float, date_str: str):
        self._cursor_price_var.set(f"{price:.5f}")
        self._cursor_date_var.set(date_str)

    # ------------------------------------------------------------------
    # Auto-rafraîchissement
    # ------------------------------------------------------------------

    def _toggle_auto_refresh(self):
        if self._auto_refresh.get():
            self._stop_refresh = False
            self._start_refresh_loop()
        else:
            self._stop_refresh = True

    def _start_refresh_loop(self):
        def _loop():
            while not self._stop_refresh and self._auto_refresh.get():
                secs = self._refresh_sec.get()
                for _ in range(secs * 2):
                    if self._stop_refresh:
                        return
                    time.sleep(0.5)
                if not self._stop_refresh:
                    self.after(0, self.load_data)

        self._refresh_thread = threading.Thread(target=_loop, daemon=True)
        self._refresh_thread.start()

    # ------------------------------------------------------------------
    # TTK Style
    # ------------------------------------------------------------------

    def _apply_ttk_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(
            "TCombobox",
            fieldbackground=THEME["bg_panel"],
            background=THEME["bg_panel"],
            foreground=THEME["text"],
            selectbackground=THEME["bg_panel"],
            selectforeground=THEME["accent"],
            borderwidth=0,
            arrowcolor=THEME["text_secondary"],
        )
        s.map("TCombobox",
              fieldbackground=[("readonly", THEME["bg_panel"])],
              foreground=[("readonly", THEME["text"])],
              background=[("readonly", THEME["bg_panel"])])

    # ------------------------------------------------------------------
    # Fermeture propre
    # ------------------------------------------------------------------

    def destroy(self):
        self._stop_refresh = True
        super().destroy()
