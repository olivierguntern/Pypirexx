"""Configuration : paires forex, unités de temps, thème visuel."""

FOREX_PAIRS = {
    "Majeures": [
        ("EUR/USD", "EURUSD=X"),
        ("GBP/USD", "GBPUSD=X"),
        ("USD/JPY", "USDJPY=X"),
        ("USD/CHF", "USDCHF=X"),
        ("AUD/USD", "AUDUSD=X"),
        ("USD/CAD", "USDCAD=X"),
        ("NZD/USD", "NZDUSD=X"),
    ],
    "Mineures": [
        ("EUR/GBP", "EURGBP=X"),
        ("EUR/JPY", "EURJPY=X"),
        ("GBP/JPY", "GBPJPY=X"),
        ("EUR/AUD", "EURAUD=X"),
        ("GBP/AUD", "GBPAUD=X"),
        ("AUD/JPY", "AUDJPY=X"),
        ("EUR/CAD", "EURCAD=X"),
        ("EUR/CHF", "EURCHF=X"),
        ("GBP/CHF", "GBPCHF=X"),
        ("CHF/JPY", "CHFJPY=X"),
    ],
    "Exotiques": [
        ("USD/MXN", "USDMXN=X"),
        ("USD/ZAR", "USDZAR=X"),
        ("USD/TRY", "USDTRY=X"),
        ("USD/SEK", "USDSEK=X"),
        ("USD/NOK", "USDNOK=X"),
        ("USD/SGD", "USDSGD=X"),
        ("USD/HKD", "USDHKD=X"),
        ("USD/PLN", "USDPLN=X"),
        ("EUR/TRY", "EURTRY=X"),
    ],
}

# (period, interval) compatibles avec yfinance
# Limites yfinance : 1m→7j, 5/15/30m→60j, 1h→730j
TIMEFRAMES = {
    "1 min":     ("7d",  "1m"),
    "5 min":     ("60d", "5m"),
    "15 min":    ("60d", "15m"),
    "30 min":    ("60d", "30m"),
    "1 heure":   ("2y",  "1h"),
    "4 heures":  ("2y",  "1h"),   # rééchantillonné depuis 1h
    "1 jour":    ("5y",  "1d"),
    "1 semaine": ("10y", "1wk"),
    "1 mois":    ("max", "1mo"),
}

THEME = {
    "bg":           "#0d1117",
    "bg_secondary": "#161b22",
    "bg_panel":     "#1c2128",
    "bg_hover":     "#21262d",
    "accent":       "#e94560",
    "accent_dark":  "#b5334a",
    "text":         "#e6edf3",
    "text_secondary": "#8b949e",
    "green":        "#3fb950",
    "red":          "#f85149",
    "yellow":       "#d29922",
    "blue":         "#58a6ff",
    "purple":       "#bc8cff",
    "cyan":         "#39d353",
    "border":       "#30363d",
}

INDICATOR_COLORS = {
    "sma20":    "#f0b429",   # or jaune
    "sma50":    "#ff7b72",   # rouge clair
    "ema20":    "#79c0ff",   # bleu clair
    "bollinger":"#d2a8ff",   # violet
    "rsi":      "#e94560",   # accent rouge
    "macd_line":"#f0b429",   # jaune
    "macd_sig": "#ff7b72",   # rouge
    "macd_pos": "#3fb950",   # vert
    "macd_neg": "#f85149",   # rouge
}
