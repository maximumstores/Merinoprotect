# -*- coding: utf-8 -*-
"""Общий модуль дашборда: БД, i18n, темы, навигация, UI-хелперы."""

import base64
import os

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

MARKETPLACE_NAMES = {
    "ATVPDKIKX0DER": "US", "A2EUQ1WTGCTBG2": "CA", "A1AM78C64UM0Y8": "MX",
    "A1F83G8C2ARO7P": "UK", "A1PA6795UKMFR9": "DE", "A13V1IB3VIYZZH": "FR",
    "APJ6JRA9NG5V4": "IT", "A1RKKUPIHCS9HS": "ES", "A1805IZSGTT6HS": "NL",
    "A2NODRKZP88ZB9": "SE", "A1C3SOZRARQ6R3": "PL",
}

AMAZON_DOMAINS = {
    "ATVPDKIKX0DER": "amazon.com", "A2EUQ1WTGCTBG2": "amazon.ca",
    "A1AM78C64UM0Y8": "amazon.com.mx", "A1F83G8C2ARO7P": "amazon.co.uk",
    "A1PA6795UKMFR9": "amazon.de", "A13V1IB3VIYZZH": "amazon.fr",
    "APJ6JRA9NG5V4": "amazon.it", "A1RKKUPIHCS9HS": "amazon.es",
    "A1805IZSGTT6HS": "amazon.nl", "A2NODRKZP88ZB9": "amazon.se",
    "A1C3SOZRARQ6R3": "amazon.pl",
}


def mp_label(mp_id: str) -> str:
    return MARKETPLACE_NAMES.get(mp_id, mp_id)


# ------------------------------------------------------------- themes ----

THEMES = {
    "dark": {
        "bg": "#0e1117", "sidebar": "#161a24", "card": "#1a1f2e",
        "border": "rgba(255,255,255,0.06)", "text": "#f0f2f6",
        "muted": "#8b93a7", "grid": "rgba(255,255,255,0.06)",
        "chart_font": "#c9d1e0", "logo_filter": "none",
    },
    "light": {
        "bg": "#f7f8fa", "sidebar": "#ffffff", "card": "#ffffff",
        "border": "rgba(0,0,0,0.08)", "text": "#1a1f2e",
        "muted": "#5b6472", "grid": "rgba(0,0,0,0.07)",
        "chart_font": "#3a4150", "logo_filter": "invert(1)",
    },
}

ACCENT = "#10b981"
ACCENT2 = "#3b82f6"


def cur_theme() -> dict:
    return THEMES[st.session_state.get("theme", "dark")]


def plotly_layout() -> dict:
    th = cur_theme()
    return dict(
        template="plotly_dark" if st.session_state.get("theme", "dark") == "dark"
                 else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=th["chart_font"], size=12),
        margin=dict(l=10, r=10, t=36, b=10),
        height=340,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=th["grid"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )


# ------------------------------------------------------------- i18n ----

TRANSLATIONS = {
    "uk": {
        "nav_overview": "📊 Огляд", "nav_stock": "📦 Залишки",
        "overview_title": "Merinoprotect — Огляд",
        "stock_title": "📦 Залишки FBA",
        "marketplace": "Маркетплейс", "period": "Період", "days": "днів",
        "orders_n": "Замовлення", "revenue": "Виручка",
        "avg_check": "Середній чек", "orders_today": "Замовлень сьогодні",
        "by_utc": "за UTC", "chart_daily": "Замовлення та виручка по днях",
        "orders_series": "Замовлення", "revenue_series": "Виручка",
        "top10_sku": "Топ-10 SKU за кількістю", "last20": "Останні 20 замовлень",
        "col_order": "Замовлення", "col_date": "Дата", "col_status": "Статус",
        "col_market": "Маркет", "col_sum": "Сума",
        "no_orders": "Немає замовлень за обраний період.",
        "search": "Пошук за SKU / назвою", "sku_in_stock": "SKU із залишком > 0",
        "total_rows": "всього рядків", "inbound_sub": "working + shipped + receiving",
        "top15_sku": "Топ-15 SKU за fulfillable", "stock_by_sku": "Залишки за SKU",
        "snapshot": "знімок", "col_name": "Назва", "col_photo": "Фото",
        "no_inventory": "Немає даних у fba_inventory — запусти 02_fba_inventory_loader.py",
        "legend_stock": "🔴 fulfillable = 0 · 🟡 fulfillable < 20",
        "cache_note": "Дані з merinoprotect · кеш 10 хв",
    },
    "ru": {
        "nav_overview": "📊 Обзор", "nav_stock": "📦 Остатки",
        "overview_title": "Merinoprotect — Обзор",
        "stock_title": "📦 Остатки FBA",
        "marketplace": "Маркетплейс", "period": "Период", "days": "дней",
        "orders_n": "Заказы", "revenue": "Выручка",
        "avg_check": "Средний чек", "orders_today": "Заказов сегодня",
        "by_utc": "по UTC", "chart_daily": "Заказы и выручка по дням",
        "orders_series": "Заказы", "revenue_series": "Выручка",
        "top10_sku": "Топ-10 SKU по количеству", "last20": "Последние 20 заказов",
        "col_order": "Заказ", "col_date": "Дата", "col_status": "Статус",
        "col_market": "Маркет", "col_sum": "Сумма",
        "no_orders": "Нет заказов за выбранный период.",
        "search": "Поиск по SKU / названию", "sku_in_stock": "SKU с остатком > 0",
        "total_rows": "всего строк", "inbound_sub": "working + shipped + receiving",
        "top15_sku": "Топ-15 SKU по fulfillable", "stock_by_sku": "Остатки по SKU",
        "snapshot": "снапшот", "col_name": "Название", "col_photo": "Фото",
        "no_inventory": "Нет данных в fba_inventory — запусти 02_fba_inventory_loader.py",
        "legend_stock": "🔴 fulfillable = 0 · 🟡 fulfillable < 20",
        "cache_note": "Данные из merinoprotect · кэш 10 мин",
    },
    "en": {
        "nav_overview": "📊 Overview", "nav_stock": "📦 Stock",
        "overview_title": "Merinoprotect — Overview",
        "stock_title": "📦 FBA Stock",
        "marketplace": "Marketplace", "period": "Period", "days": "days",
        "orders_n": "Orders", "revenue": "Revenue",
        "avg_check": "Avg order value", "orders_today": "Orders today",
        "by_utc": "UTC", "chart_daily": "Orders & revenue by day",
        "orders_series": "Orders", "revenue_series": "Revenue",
        "top10_sku": "Top-10 SKU by quantity", "last20": "Last 20 orders",
        "col_order": "Order", "col_date": "Date", "col_status": "Status",
        "col_market": "Market", "col_sum": "Total",
        "no_orders": "No orders for selected period.",
        "search": "Search SKU / name", "sku_in_stock": "SKUs in stock > 0",
        "total_rows": "total rows", "inbound_sub": "working + shipped + receiving",
        "top15_sku": "Top-15 SKU by fulfillable", "stock_by_sku": "Stock by SKU",
        "snapshot": "snapshot", "col_name": "Product name", "col_photo": "Photo",
        "no_inventory": "No data in fba_inventory — run 02_fba_inventory_loader.py",
        "legend_stock": "🔴 fulfillable = 0 · 🟡 fulfillable < 20",
        "cache_note": "Data from merinoprotect · cache 10 min",
    },
}

LANGS = ["uk", "ru", "en"]
LANG_LABELS = {"uk": "УКР", "ru": "РУС", "en": "ENG"}


def t(key: str) -> str:
    lang = st.session_state.get("lang", "uk")
    return TRANSLATIONS.get(lang, TRANSLATIONS["uk"]).get(key, key)


# ------------------------------------------------------------- sidebar ----

@st.cache_data(show_spinner=False)
def _logo_b64() -> str | None:
    """Читаем лого один раз, отдаём как base64 — не зависит от рабочих путей."""
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("logo.png", "Logo.png", "logo.PNG"):
        p = os.path.join(here, "assets", name)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None


def lang_selector() -> str:
    """Сайдбар: лого + навігація + мова + тема."""
    if "lang" not in st.session_state:
        st.session_state["lang"] = "uk"
    if "theme" not in st.session_state:
        st.session_state["theme"] = "dark"

    with st.sidebar:
        b64 = _logo_b64()
        if b64:
            st.markdown(
                f'<div style="padding: 4px 0 14px 0; text-align: center;">'
                f'<img class="mp-logo" src="data:image/png;base64,{b64}" '
                f'style="max-width: 175px; width: 100%;" /></div>',
                unsafe_allow_html=True,
            )
        st.page_link("app.py", label=t("nav_overview"))
        st.page_link("pages/1_Stock.py", label=t("nav_stock"))
        st.markdown("---")

        cols = st.columns(3)
        for i, code in enumerate(LANGS):
            with cols[i]:
                if st.button(
                    LANG_LABELS[code], key=f"lang_{code}",
                    type="primary" if st.session_state["lang"] == code else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["lang"] = code
                    st.rerun()

        tc1, tc2 = st.columns(2)
        with tc1:
            if st.button("🌙 Dark", key="th_dark", use_container_width=True,
                         type="primary" if st.session_state["theme"] == "dark" else "secondary"):
                st.session_state["theme"] = "dark"
                st.rerun()
        with tc2:
            if st.button("☀️ Light", key="th_light", use_container_width=True,
                         type="primary" if st.session_state["theme"] == "light" else "secondary"):
                st.session_state["theme"] = "light"
                st.rerun()

    return st.session_state["lang"]


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
        raise RuntimeError("DATABASE_URL не знайдено ні в st.secrets, ні в .env")
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

def inject_css():
    th = cur_theme()
    st.markdown(f"""
<style>
[data-testid="stSidebarNav"] {{ display: none; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}

.stApp {{ background: {th["bg"]}; }}
[data-testid="stSidebar"] {{ background: {th["sidebar"]}; }}
.stApp, .stApp p, .stApp span, .stApp label,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: {th["text"]}; }}
.stCaption, .stApp small {{ color: {th["muted"]} !important; }}

.mp-logo {{ filter: {th["logo_filter"]}; }}

.block-container {{ padding-top: 1.6rem; padding-bottom: 2rem; }}
header[data-testid="stHeader"] {{ background: transparent; }}

.mp-card {{
    background: {th["card"]};
    border: 1px solid {th["border"]};
    border-radius: 12px;
    padding: 16px 18px;
    height: 100%;
}}
.mp-card .t {{ color: {th["muted"]}; font-size: 13px; margin-bottom: 6px; white-space: nowrap; }}
.mp-card .v {{ color: {th["text"]}; font-size: 28px; font-weight: 700; line-height: 1.15; }}
.mp-card .s {{ color: {th["muted"]}; font-size: 12px; margin-top: 4px; }}
.mp-card .d-up   {{ color: #10b981; font-size: 13px; margin-top: 4px; }}
.mp-card .d-down {{ color: #ef4444; font-size: 13px; margin-top: 4px; }}

div[data-testid="stDataFrame"] {{ font-size: 13px; }}
h1, h2, h3 {{ letter-spacing: -0.02em; }}
</style>
""", unsafe_allow_html=True)


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


# Обратная совместимость: если где-то остался PLOTLY_LAYOUT — тёмный по умолчанию
PLOTLY_LAYOUT = plotly_layout() if hasattr(st, "session_state") else {}
