# -*- coding: utf-8 -*-
"""Общие функции дашборда Merinoprotect: подключение к БД, запросы, UI-хелперы."""

import os

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

MARKETPLACE_NAMES = {
    "ATVPDKIKX0DER": "🇺�🇸 US",
    "A2EUQ1WTGCTBG2": "🇨🇦 CA",
    "A1AM78C64UM0Y8": "🇲🇽 MX",
    "A1F83G8C2ARO7P": "🇬🇧 UK",
    "A1PA6795UKMFR9": "🇩🇪 DE",
    "A13V1IB3VIYZZH": "🇫🇷 FR",
    "APJ6JRA9NG5V4": "🇮🇹 IT",
    "A1RKKUPIHCS9HS": "🇪🇸 ES",
    "A1805IZSGTT6HS": "🇳🇱 NL",
    "A2NODRKZP88ZB9": "🇸🇪 SE",
    "A1C3SOZRARQ6R3": "🇵🇱 PL",
}


def mp_label(mp_id: str) -> str:
    return MARKETPLACE_NAMES.get(mp_id, mp_id)


def _database_url() -> str:
    # 1) Streamlit Cloud secrets, 2) локальный .env проекта
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(os.path.dirname(here), ".env"), override=False)
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL не найден ни в st.secrets, ни в .env")
    return url


@st.cache_resource
def get_conn():
    conn = psycopg2.connect(_database_url())
    conn.autocommit = True
    return conn


@st.cache_data(ttl=600, show_spinner=False)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Запрос к БД -> DataFrame. Кэш 10 минут."""
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn, params=params)
    except Exception:
        # соединение могло протухнуть — пересоздаём один раз
        get_conn.clear()
        conn = get_conn()
        return pd.read_sql(sql, conn, params=params)


# ---------------------------------------------------------------- UI ----

CSS = """
<style>
.block-container { padding-top: 1.6rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { background: transparent; }

.mp-card {
    background: #1a1f2e;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 16px 18px;
    height: 100%;
}
.mp-card .t {
    color: #8b93a7;
    font-size: 13px;
    margin-bottom: 6px;
    white-space: nowrap;
}
.mp-card .v {
    color: #f0f2f6;
    font-size: 28px;
    font-weight: 700;
    line-height: 1.15;
}
.mp-card .s {
    color: #8b93a7;
    font-size: 12px;
    margin-top: 4px;
}
.mp-card .d-up   { color: #10b981; font-size: 13px; margin-top: 4px; }
.mp-card .d-down { color: #ef4444; font-size: 13px; margin-top: 4px; }

div[data-testid="stDataFrame"] { font-size: 13px; }

h1, h2, h3 { letter-spacing: -0.02em; }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def metric_card(title: str, value: str, delta: str | None = None,
                delta_up: bool = True, sub: str | None = None):
    d = ""
    if delta:
        cls = "d-up" if delta_up else "d-down"
        arrow = "▲" if delta_up else "▼"
        d = f'<div class="{cls}">{arrow} {delta}</div>'
    s = f'<div class="s">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="mp-card"><div class="t">{title}</div>'
        f'<div class="v">{value}</div>{d}{s}</div>',
        unsafe_allow_html=True,
    )


PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#c9d1e0", size=12),
    margin=dict(l=10, r=10, t=36, b=10),
    height=340,
    xaxis=dict(showgrid=False),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)

ACCENT = "#10b981"
ACCENT2 = "#3b82f6"
