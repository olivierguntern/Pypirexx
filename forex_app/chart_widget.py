"""Widget tkinter encapsulant un graphique mplfinance avec indicateurs techniques."""

import tkinter as tk
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import mplfinance as mpf

from forex_app.config import THEME, INDICATOR_COLORS
from forex_app.data_fetcher import (
    calc_sma, calc_ema, calc_bollinger,
    calc_rsi, calc_macd,
)

matplotlib.use("TkAgg")

# ---------------------------------------------------------------------------
# Style mplfinance sombre personnalisé
# ---------------------------------------------------------------------------

def _build_mpf_style() -> object:
    mc = mpf.make_marketcolors(
        up=THEME["green"],
        down=THEME["red"],
        wick={"up": THEME["green"], "down": THEME["red"]},
        edge={"up": THEME["green"], "down": THEME["red"]},
        volume={"up": "#3fb95060", "down": "#f8514960"},
    )
    return mpf.make_mpf_style(
        marketcolors=mc,
        facecolor=THEME["bg"],
        edgecolor=THEME["bg_panel"],
        figcolor=THEME["bg"],
        gridcolor=THEME["border"],
        gridstyle="--",
        gridaxis="both",
        y_on_right=True,
        rc={
            "axes.labelcolor": THEME["text_secondary"],
            "xtick.color": THEME["text_secondary"],
            "ytick.color": THEME["text_secondary"],
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "text.color": THEME["text"],
            "font.family": "monospace",
            "axes.titlesize": 11,
            "axes.titlecolor": THEME["text"],
        },
    )


MPF_STYLE = _build_mpf_style()


# ---------------------------------------------------------------------------
# ChartWidget
# ---------------------------------------------------------------------------

class ChartWidget(tk.Frame):
    """
    Widget affichant un graphique en chandeliers avec indicateurs.
    Peut être inséré dans n'importe quel conteneur tkinter.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=THEME["bg"], **kwargs)
        self.fig: plt.Figure | None = None
        self.canvas: FigureCanvasTkAgg | None = None
        self._toolbar_frame: tk.Frame | None = None
        self._crosshair_vline = None
        self._crosshair_hline = None
        self._price_annotation = None
        self._main_ax = None
        self.on_cursor_move = None   # callback(price, date_str)

        self._show_placeholder()

    # ------------------------------------------------------------------
    # Affichage initial
    # ------------------------------------------------------------------

    def _show_placeholder(self):
        """Affiche un message d'accueil avant le premier chargement."""
        self._placeholder = tk.Frame(self, bg=THEME["bg"])
        self._placeholder.place(relx=0, rely=0, relwidth=1, relheight=1)

        tk.Label(
            self._placeholder,
            text="Pypirex",
            font=("Helvetica", 32, "bold"),
            bg=THEME["bg"],
            fg=THEME["accent"],
        ).pack(expand=True, pady=(80, 5))

        tk.Label(
            self._placeholder,
            text="Sélectionnez une paire et cliquez sur Actualiser",
            font=("Helvetica", 12),
            bg=THEME["bg"],
            fg=THEME["text_secondary"],
        ).pack()

    def _hide_placeholder(self):
        if self._placeholder:
            self._placeholder.destroy()
            self._placeholder = None

    # ------------------------------------------------------------------
    # Rendu du graphique
    # ------------------------------------------------------------------

    def update_chart(self, df: pd.DataFrame, symbol_name: str, indicators: dict):
        """
        Recrée le graphique avec les nouvelles données et indicateurs.

        Args:
            df:          DataFrame OHLCV indexé par datetime
            symbol_name: nom affiché (ex: "EUR/USD")
            indicators:  dict {clé: bool} pour chaque indicateur
        """
        if df is None or df.empty or len(df) < 2:
            self._show_error("Données insuffisantes pour afficher le graphique.")
            return

        self._hide_placeholder()
        self._clear_chart()

        apds = []
        panel_ratios = [5, 1.2]   # prix, volume
        next_panel = 2

        close = df["Close"]

        # ── Indicateurs en superposition (panel 0) ──────────────────────
        if indicators.get("sma20") and len(df) >= 20:
            sma20 = calc_sma(close, 20)
            apds.append(mpf.make_addplot(
                sma20, panel=0, color=INDICATOR_COLORS["sma20"],
                width=1.2, label="SMA 20",
            ))

        if indicators.get("sma50") and len(df) >= 50:
            sma50 = calc_sma(close, 50)
            apds.append(mpf.make_addplot(
                sma50, panel=0, color=INDICATOR_COLORS["sma50"],
                width=1.2, label="SMA 50",
            ))

        if indicators.get("ema20") and len(df) >= 20:
            ema20 = calc_ema(close, 20)
            apds.append(mpf.make_addplot(
                ema20, panel=0, color=INDICATOR_COLORS["ema20"],
                width=1.2, label="EMA 20",
            ))

        if indicators.get("bollinger") and len(df) >= 20:
            upper, mid, lower = calc_bollinger(close)
            apds.append(mpf.make_addplot(
                upper, panel=0, color=INDICATOR_COLORS["bollinger"],
                width=1.0, linestyle="--", label="BB sup",
            ))
            apds.append(mpf.make_addplot(
                mid, panel=0, color=INDICATOR_COLORS["bollinger"],
                width=0.8, linestyle="-",
            ))
            apds.append(mpf.make_addplot(
                lower, panel=0, color=INDICATOR_COLORS["bollinger"],
                width=1.0, linestyle="--", label="BB inf",
            ))

        # ── RSI (panel séparé) ──────────────────────────────────────────
        if indicators.get("rsi") and len(df) >= 15:
            rsi = calc_rsi(close)
            rsi_panel = next_panel
            next_panel += 1
            panel_ratios.append(1.8)

            apds.append(mpf.make_addplot(
                rsi, panel=rsi_panel,
                color=INDICATOR_COLORS["rsi"], width=1.3, ylabel="RSI",
            ))
            apds.append(mpf.make_addplot(
                pd.Series(70, index=df.index, dtype=float),
                panel=rsi_panel, color="#f85149", width=0.7, linestyle="--",
            ))
            apds.append(mpf.make_addplot(
                pd.Series(30, index=df.index, dtype=float),
                panel=rsi_panel, color="#3fb950", width=0.7, linestyle="--",
            ))
            apds.append(mpf.make_addplot(
                pd.Series(50, index=df.index, dtype=float),
                panel=rsi_panel, color=THEME["border"], width=0.5, linestyle=":",
            ))

        # ── MACD (panel séparé) ─────────────────────────────────────────
        if indicators.get("macd") and len(df) >= 27:
            macd_line, signal_line, histogram = calc_macd(close)
            macd_panel = next_panel
            next_panel += 1
            panel_ratios.append(1.8)

            apds.append(mpf.make_addplot(
                macd_line, panel=macd_panel,
                color=INDICATOR_COLORS["macd_line"], width=1.2, ylabel="MACD",
            ))
            apds.append(mpf.make_addplot(
                signal_line, panel=macd_panel,
                color=INDICATOR_COLORS["macd_sig"], width=1.0,
            ))
            # Histogramme : barres vertes (positif) et rouges (négatif)
            hist_pos = histogram.clip(lower=0)
            hist_neg = histogram.clip(upper=0)
            apds.append(mpf.make_addplot(
                hist_pos, panel=macd_panel, type="bar",
                color=INDICATOR_COLORS["macd_pos"], alpha=0.75, width=0.8,
            ))
            apds.append(mpf.make_addplot(
                hist_neg, panel=macd_panel, type="bar",
                color=INDICATOR_COLORS["macd_neg"], alpha=0.75, width=0.8,
            ))

        # ── Rendu mplfinance ────────────────────────────────────────────
        plot_kwargs = dict(
            type="candle",
            style=MPF_STYLE,
            volume=True,
            panel_ratios=tuple(panel_ratios),
            returnfig=True,
            figsize=(14, 9),
            tight_layout=True,
            warn_too_much_data=10_000,
        )
        if apds:
            plot_kwargs["addplot"] = apds

        try:
            self.fig, axes = mpf.plot(df, **plot_kwargs)
        except Exception as exc:
            self._show_error(f"Erreur de rendu : {exc}")
            return

        self.fig.patch.set_facecolor(THEME["bg"])
        self._main_ax = axes[0]

        # Titre
        self._main_ax.set_title(
            f"  {symbol_name}", loc="left",
            color=THEME["text"], fontsize=11, fontweight="bold",
        )

        # ── Intégration tkinter ─────────────────────────────────────────
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()

        self._toolbar_frame = tk.Frame(self, bg=THEME["bg_panel"], height=32)
        self._toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        toolbar = NavigationToolbar2Tk(self.canvas, self._toolbar_frame)
        toolbar.config(background=THEME["bg_panel"])
        for btn in toolbar.winfo_children():
            try:
                btn.config(background=THEME["bg_panel"], foreground=THEME["text"])
            except tk.TclError:
                pass
        toolbar.update()

        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Redimensionnement dynamique
        self.canvas.get_tk_widget().bind("<Configure>", self._on_resize)

        # Crosshair interactif
        self._setup_crosshair()

    # ------------------------------------------------------------------
    # Crosshair interactif
    # ------------------------------------------------------------------

    def _setup_crosshair(self):
        """Ajoute un réticule qui suit la souris."""
        if self.fig is None or self._main_ax is None:
            return

        ax = self._main_ax
        self._crosshair_vline = ax.axvline(
            color=THEME["text_secondary"], linewidth=0.6,
            linestyle="--", alpha=0.6, visible=False,
        )
        self._crosshair_hline = ax.axhline(
            color=THEME["text_secondary"], linewidth=0.6,
            linestyle="--", alpha=0.6, visible=False,
        )
        self._price_annotation = ax.annotate(
            "", xy=(0, 0), xycoords="data",
            bbox=dict(boxstyle="round,pad=0.3", fc=THEME["bg_panel"],
                      ec=THEME["border"], alpha=0.85),
            color=THEME["text"], fontsize=7.5,
            annotation_clip=False, visible=False,
        )

        def _on_move(event):
            if event.inaxes != ax or event.xdata is None:
                self._crosshair_vline.set_visible(False)
                self._crosshair_hline.set_visible(False)
                self._price_annotation.set_visible(False)
                self.canvas.draw_idle()
                return

            self._crosshair_vline.set_xdata([event.xdata])
            self._crosshair_vline.set_visible(True)
            self._crosshair_hline.set_ydata([event.ydata])
            self._crosshair_hline.set_visible(True)

            price_str = f"{event.ydata:.5f}"
            self._price_annotation.set_text(price_str)
            self._price_annotation.xy = (event.xdata, event.ydata)
            self._price_annotation.set_visible(True)

            self.canvas.draw_idle()

            if self.on_cursor_move:
                try:
                    import matplotlib.dates as mdates
                    date_str = mdates.num2date(event.xdata).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = ""
                self.on_cursor_move(event.ydata, date_str)

        self.fig.canvas.mpl_connect("motion_notify_event", _on_move)

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def _on_resize(self, event):
        """Redimensionne la figure quand le widget est redimensionné."""
        if self.fig is None or self.canvas is None:
            return
        w = event.width / self.fig.dpi
        h = event.height / self.fig.dpi
        if w > 1 and h > 1:
            self.fig.set_size_inches(w, h, forward=False)
            self.canvas.draw_idle()

    def _clear_chart(self):
        """Détruit les widgets du graphique précédent."""
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        if self._toolbar_frame:
            self._toolbar_frame.destroy()
            self._toolbar_frame = None
        if self.fig:
            plt.close(self.fig)
            self.fig = None
        self._main_ax = None

    def _show_error(self, message: str):
        """Affiche un message d'erreur à la place du graphique."""
        self._clear_chart()
        frame = tk.Frame(self, bg=THEME["bg"])
        frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(
            frame,
            text=message,
            bg=THEME["bg"],
            fg=THEME["red"],
            font=("Helvetica", 11),
            wraplength=500,
        ).pack(expand=True)
