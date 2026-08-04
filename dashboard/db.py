# -*- coding: utf-8 -*-
"""Общие функции дашборда Merinoprotect: БД, i18n, UI-хелперы."""

import os

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

MARKETPLACE_NAMES = {
    "ATVPDKIKX0DER": "US",
    "A2EUQ1WTGCTBG2": "CA",
    "A1AM78C64UM0Y8": "MX",
    "A1F83G8C2ARO7P": "UK",
    "A1PA6795UKMFR9": "DE",
    "A13V1IB3VIYZZH": "FR",
    "APJ6JRA9NG5V4": "IT",
    "A1RKKUPIHCS9HS": "ES",
    "A1805IZSGTT6HS": "NL",
    "A2NODRKZP88ZB9": "SE",
    "A1C3SOZRARQ6R3": "PL",
}


def mp_label(mp_id: str) -> str:
    return MARKETPLACE_NAMES.get(mp_id, mp_id)


# ------------------------------------------------------------- i18n ----

TRANSLATIONS = {
    "ru": {
        "overview_title": "🐑 Merinoprotect — Обзор",
        "stock_title": "📦 Остатки FBA",
        "marketplace": "Маркетплейс",
        "period": "Период",
        "days": "дней",
        "orders_n": "Заказы",
        "revenue": "Выручка",
        "avg_check": "Средний чек",
        "orders_today": "Заказов сегодня",
        "by_utc": "по UTC",
        "chart_daily": "Заказы и выручка по дням",
        "orders_series": "Заказы",
        "revenue_series": "Выручка",
        "top10_sku": "Топ-10 SKU по количеству",
        "last20": "Последние 20 заказов",
        "col_order": "Заказ",
        "col_date": "Дата",
        "col_status": "Статус",
        "col_market": "Маркет",
        "col_sum": "Сумма",
        "no_orders": "Нет заказов за выбранный период.",
        "search": "Поиск по SKU / названию",
        "sku_in_stock": "SKU с остатком > 0",
        "total_rows": "всего строк",
        "inbound_sub": "working + shipped + receiving",
        "top15_sku": "Топ-15 SKU по fulfillable",
        "stock_by_sku": "Остатки по SKU",
        "snapshot": "снапшот",
        "col_name": "Название",
        "no_inventory": "Нет данных в fba_inventory — запусти 02_fba_inventory_loader.py",
        "legend_stock": "🔴 fulfillable = 0 · 🟡 fulfillable < 20",
        "cache_note": "Данные из merinoprotect · кэш 10 мин",
    },
    "en": {
        "overview_title": "🐑 Merinoprotect — Overview",
        "stock_title": "📦 FBA Stock",
        "marketplace": "Marketplace",
        "period": "Period",
        "days": "days",
        "orders_n": "Orders",
        "revenue": "Revenue",
        "avg_check": "Avg order value",
        "orders_today": "Orders today",
        "by_utc": "UTC",
        "chart_daily": "Orders & revenue by day",
        "orders_series": "Orders",
        "revenue_series": "Revenue",
        "top10_sku": "Top-10 SKU by quantity",
        "last20": "Last 20 orders",
        "col_order": "Order",
        "col_date": "Date",
        "col_status": "Status",
        "col_market": "Market",
        "col_sum": "Total",
        "no_orders": "No orders for selected period.",
        "search": "Search SKU / name",
        "sku_in_stock": "SKUs in stock > 0",
        "total_rows": "total rows",
        "inbound_sub": "working + shipped + receiving",
        "top15_sku": "Top-15 SKU by fulfillable",
        "stock_by_sku": "Stock by SKU",
        "snapshot": "snapshot",
        "col_name": "Product name",
        "no_inventory": "No data in fba_inventory — run 02_fba_inventory_loader.py",
        "legend_stock": "🔴 fulfillable = 0 · 🟡 fulfillable < 20",
        "cache_note": "Data from merinoprotect · cache 10 min",
    },
}


def lang_selector() -> str:
    """Переключатель языка в сайдбаре. Возвращает код языка."""
    if "lang" not in st.session_state:
        st.session_state["lang"] = "ru"
    with st.sidebar:
        st.radio(
            "Language / Язык",
            options=["ru", "en"],
            format_func=lambda x: {"ru": "🇷🇺 Русский", "en": "🇬🇧 English"}[x],
            key="lang",
        )
    return st.session_state["lang"]


def t(key: str) -> str:
    lang = st.session_state.get("lang", "ru")
    return TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(key, key)


# ---------------------------------------------------------------- DB ----

def _database_url() -> str:
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
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn, params=params)
    except Exception:
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
.mp-card .t { color: #8b93a7; font-size: 13px; margin-bottom: 6px; white-space: nowrap; }
.mp-card .v { color: #f0f2f6; font-size: 28px; font-weight: 700; line-height: 1.15; }
.mp-card .s { color: #8b93a7; font-size: 12px; margin-top: 4px; }
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
