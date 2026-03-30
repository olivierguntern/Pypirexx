"""Récupération des données forex via yfinance et calcul des indicateurs techniques."""

import yfinance as yf
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Récupération des données OHLCV
# ---------------------------------------------------------------------------

def fetch_ohlcv(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """
    Récupère les données OHLCV depuis Yahoo Finance.

    Args:
        symbol:   ticker yfinance (ex: "EURUSD=X")
        period:   période historique (ex: "1y", "5y", "max")
        interval: intervalle des bougies (ex: "1d", "1h", "5m")

    Returns:
        DataFrame avec colonnes Open/High/Low/Close/Volume, indexé par datetime.
        Retourne un DataFrame vide en cas d'échec.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            return pd.DataFrame()

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

        # Supprimer le fuseau horaire pour mplfinance
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)

        # Supprimer les lignes avec NaN sur OHLC
        df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)

        return df

    except Exception as exc:
        raise RuntimeError(f"Impossible de charger {symbol}: {exc}") from exc


def resample_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    """Rééchantillonne des données 1h en 4h."""
    resampled = df_1h.resample("4h").agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
        Volume=("Volume", "sum"),
    )
    return resampled.dropna(subset=["Open", "High", "Low", "Close"])


# ---------------------------------------------------------------------------
# Indicateurs techniques
# ---------------------------------------------------------------------------

def calc_sma(series: pd.Series, period: int) -> pd.Series:
    """Moyenne Mobile Simple."""
    return series.rolling(window=period, min_periods=period).mean()


def calc_ema(series: pd.Series, period: int) -> pd.Series:
    """Moyenne Mobile Exponentielle."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def calc_bollinger(series: pd.Series, period: int = 20, nb_std: float = 2.0):
    """
    Bandes de Bollinger.

    Returns:
        (upper, middle, lower) en tant que pd.Series
    """
    middle = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + nb_std * std
    lower = middle - nb_std * std
    return upper, middle, lower


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (méthode Wilder / EWM).
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    MACD : ligne MACD, ligne signal, histogramme.

    Returns:
        (macd_line, signal_line, histogram) en tant que pd.Series
    """
    ema_fast = series.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = series.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
