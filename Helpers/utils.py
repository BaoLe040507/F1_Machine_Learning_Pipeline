from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
import requests

# Optional: keep type hints if you want
from supabase import Client, create_client  # type: ignore

import streamlit as st

@st.cache_resource
def get_supabase() -> Client:
    # 1) Try Streamlit secrets first
    try:
        if "supabase" in st.secrets:
            sup = st.secrets["supabase"]
            url = sup.get("url")
            key = sup.get("key")
            if url and key:
                return create_client(url, key)
    except Exception:
        pass

    # 2) Fallback to local secrets.toml
    url, key = _load_secrets_from_toml()
    if url and key:
        try:
            return create_client(url, key)
        except Exception as e:
            print(f"[ERROR] Failed to initialize Supabase client from secrets.toml: {e}")

    raise RuntimeError("Could not initialize Supabase client: missing credentials in st.secrets or secrets.toml")

# Optional alias to match any existing usage
get_supabase_client = get_supabase

def _load_secrets_from_toml() -> Tuple[Optional[str], Optional[str]]:
    """
    Load secrets from .streamlit/secrets.toml by searching up from this file.
    Returns (url, key) or (None, None) if not found / parse fails.
    """
    try:
        root = Path(__file__).resolve()
        found = None
        # Look for .streamlit/secrets.toml in this repo
        for base in [root] + list(root.parents):
            candidate = base / ".streamlit" / "secrets.toml"
            if candidate.exists():
                found = candidate
                break
        if not found:
            return None, None

        text = found.read_text(encoding="utf-8")
        try:
            import tomllib  # Python 3.11+
            data = tomllib.loads(text)
        except Exception:
            import tomli as toml  # type: ignore
            data = toml.loads(text)

        url = data.get("supabase", {}).get("url")
        key = data.get("supabase", {}).get("key")
        return url, key
    except Exception as e:
        print(f"[WARN] Could not load secrets from secrets.toml: {e}")
        return None, None

supabase = get_supabase()
# get df from supabase
def get_supabase_df(table_name: str, batch_size: int = 1000, select: str = "*") -> pd.DataFrame:
    """
    Retrieve all rows from a Supabase table by paginating through batches.

    Parameters
    ----------
    table_name : str
        Name of the Supabase table.
    batch_size : int, optional
        Number of rows to fetch per batch (default 1000).
    select : str, optional
        Columns to select, e.g. "*" or "id, name" (default "*").

    Returns
    -------
    pd.DataFrame
        DataFrame containing all rows from the table.
    """
    offset = 0
    all_rows = []

    while True:
        response = (
            supabase.table(table_name)
            .select(select)
            .range(offset, offset + batch_size - 1)  # inclusive range
            .execute()
        )
        data = response.data

        if not data:
            break

        all_rows.extend(data)
        offset += batch_size

    return pd.DataFrame(all_rows)

def get_latest_meeting():
    sessions = get_supabase_df("sessions")  # pulls from Supabase or OpenF1
    sessions["date_start"] = pd.to_datetime(sessions["date_start"])
    recent = sessions.sort_values("date_start").iloc[-1]
    return recent

