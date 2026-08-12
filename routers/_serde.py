"""_serde.py — pure-pandas response serializer (extracted from router copy-paste).

vns_api routers wrap sponsor-library returns as {"data": _clean_dataframe(...)}.
This module is intentionally pandas-only (no vnstock_data import) so it can be
unit-tested without the device-licensed sponsor package.

Handles: None, pd.DataFrame, pd.Series, dict, list → JSON-safe list of records.

Root cause fixed here (WS1a1 membership contract): sponsor calls like
Listing.symbols_by_group() return a pd.Series, but the copy-pasted
_clean_dataframe only handled None/DataFrame/dict/list and returned [] for a
Series — so /reference/equity/list_by_group silently returned {"data": []}.
"""
import pandas as pd


def _clean_dataframe(df):
    if df is None:
        return []
    # pd.Series → normalize to a single-column DataFrame so the records path
    # applies. A Series named "symbol" → [{"symbol": "ACB"}, ...].
    if isinstance(df, pd.Series):
        df = df.to_frame()
    if isinstance(df, pd.DataFrame):
        if df.empty:
            return []
        # Flatten MultiIndex columns if any
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
        df_clean = df.astype(object).where(pd.notnull(df), None)
        return df_clean.to_dict(orient="records")
    if isinstance(df, dict):
        return [df]
    if isinstance(df, list):
        return df
    return []
