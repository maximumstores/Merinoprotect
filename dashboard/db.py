# -*- coding: utf-8 -*-
"""Общий модуль дашборда: БД, i18n, темы, навигация, UI-хелперы, HTML-таблицы."""

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
        "border": "rgba(255,255,255,0.08)", "text": "#f0f2f6",
        "muted": "#8b93a7", "grid": "rgba(255,255,255,0.06)",
        "chart_font": "#c9d1e0", "logo_filter": "none",
        "row_hover": "rgba(16,185,129,0.08)",
    },
    "light": {
        "bg": "#f7f8fa", "sidebar": "#ffffff", "card": "#ffffff",
        "border": "rgba(0,0,0,0.10)", "text": "#1a1f2e",
        "muted": "#5b6472", "grid": "rgba(0,0,0,0.07)",
        "chart_font": "#1a1f2e", "logo_filter": "invert(1)",
        "row_hover": "rgba(16,185,129,0.08)",
    },
}

ACCENT = "#10b981"
ACCENT2 = "#3b82f6"


def cur_theme() -> dict:
    return THEMES[st.session_state.get("theme", "dark")]


def plotly_layout(title: str | None = None) -> dict:
    """Базовий layout для plotly. Якщо передано title — колір title
    примусово прив'язується до теми (інакше на світлій темі текст
    заголовку лишається білим і зникає)."""
    th = cur_theme()
    layout = dict(
        template="plotly_dark" if st.session_state.get("theme", "dark") == "dark"
                 else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=th["chart_font"], size=12),
        margin=dict(l=10, r=10, t=44, b=36),
        height=340,
        xaxis=dict(showgrid=False, color=th["chart_font"],
                   tickfont=dict(color=th["chart_font"])),
        yaxis=dict(gridcolor=th["grid"], color=th["chart_font"],
                   tickfont=dict(color=th["chart_font"])),
        legend=dict(orientation="h", yanchor="top", y=-0.15, x=0,
                    font=dict(color=th["chart_font"])),
    )
    if title:
        layout["title"] = dict(
            text=title, x=0.01, xanchor="left",
            font=dict(color=th["chart_font"], size=15),
            pad=dict(b=14),
        )
    return layout


# ------------------------------------------------------------- i18n ----

TRANSLATIONS = {
    "uk": {
        "nav_overview": "Огляд", "nav_stock": "Залишки",
        "overview_title": "Merinoprotect — Огляд",
        "stock_title": "Залишки FBA",
        "marketplace": "Маркетплейс", "period": "Період", "days": "днів",
        "today_option": "Сьогодні",
        "pending_note": "очікує підтвердження",
        "sort_hint": "Сортування застосовується до таблиці нижче",
        "search_orders": "Пошук за ASIN / номером замовлення (можна декілька через кому)",
        "conversion_label": "Конверсія", "sessions_label": "сесій",
        "orders_n": "Замовлення", "revenue": "Виручка",
        "avg_check": "Середній чек", "orders_today": "Замовлень сьогодні",
        "by_utc": "за UTC", "chart_daily": "Замовлення та виручка по днях",
        "orders_series": "Замовлення", "revenue_series": "Виручка",
        "top10_sku": "Топ-10 SKU за кількістю", "last20": "Останні 20 замовлень",
        "col_order": "Замовлення", "col_date": "Дата", "col_status": "Статус",
        "col_market": "Маркет", "col_sum": "Сума",
        "no_orders": "Немає замовлень за обраний період.",
        "search": "Пошук за SKU / ASIN / назвою (можна декілька через кому)", "sku_in_stock": "SKU із залишком > 0",
        "total_rows": "всього рядків", "inbound_sub": "working + shipped + receiving",
        "top15_sku": "Топ-15 SKU за fulfillable", "stock_by_sku": "Залишки за SKU",
        "snapshot": "знімок", "col_name": "Назва", "col_photo": "Фото",
        "col_qty": "Кількість",
        "no_inventory": "Немає даних у fba_inventory — запусти 02_fba_inventory_loader.py",
        "legend_stock": "🔴 fulfillable = 0 · 🟡 fulfillable < 20",
        "cache_note": "Дані з merinoprotect · кеш 10 хв",
        "sort_by": "Сортувати за", "sort_asc": "За зростанням", "sort_desc": "За спаданням",
        "sort_order_label": "Порядок",
    },
    "ru": {
        "nav_overview": "Обзор", "nav_stock": "Остатки",
        "overview_title": "Merinoprotect — Обзор",
        "stock_title": "Остатки FBA",
        "marketplace": "Маркетплейс", "period": "Период", "days": "дней",
        "today_option": "Сегодня",
        "pending_note": "ожидает подтверждения",
        "sort_hint": "Сортировка применяется к таблице ниже",
        "search_orders": "Поиск по ASIN / номеру заказа (можно несколько через запятую)",
        "conversion_label": "Конверсия", "sessions_label": "сессий",
        "orders_n": "Заказы", "revenue": "Выручка",
        "avg_check": "Средний чек", "orders_today": "Заказов сегодня",
        "by_utc": "по UTC", "chart_daily": "Заказы и выручка по дням",
        "orders_series": "Заказы", "revenue_series": "Выручка",
        "top10_sku": "Топ-10 SKU по количеству", "last20": "Последние 20 заказов",
        "col_order": "Заказ", "col_date": "Дата", "col_status": "Статус",
        "col_market": "Маркет", "col_sum": "Сумма",
        "no_orders": "Нет заказов за выбранный период.",
        "search": "Поиск по SKU / ASIN / названию (можно несколько через запятую)", "sku_in_stock": "SKU с остатком > 0",
        "total_rows": "всего строк", "inbound_sub": "working + shipped + receiving",
        "top15_sku": "Топ-15 SKU по fulfillable", "stock_by_sku": "Остатки по SKU",
        "snapshot": "снапшот", "col_name": "Название", "col_photo": "Фото",
        "col_qty": "Кол-во",
        "no_inventory": "Нет данных в fba_inventory — запусти 02_fba_inventory_loader.py",
        "legend_stock": "🔴 fulfillable = 0 · 🟡 fulfillable < 20",
        "cache_note": "Данные из merinoprotect · кэш 10 мин",
        "sort_by": "Сортировать по", "sort_asc": "По возрастанию", "sort_desc": "По убыванию",
        "sort_order_label": "Порядок",
    },
    "en": {
        "nav_overview": "Overview", "nav_stock": "Stock",
        "overview_title": "Merinoprotect — Overview",
        "stock_title": "FBA Stock",
        "marketplace": "Marketplace", "period": "Period", "days": "days",
        "today_option": "Today",
        "pending_note": "pending confirmation",
        "sort_hint": "Sorting applies to the table below",
        "search_orders": "Search ASIN / order number (comma-separated for multiple)",
        "conversion_label": "Conversion", "sessions_label": "sessions",
        "orders_n": "Orders", "revenue": "Revenue",
        "avg_check": "Avg order value", "orders_today": "Orders today",
        "by_utc": "UTC", "chart_daily": "Orders & revenue by day",
        "orders_series": "Orders", "revenue_series": "Revenue",
        "top10_sku": "Top-10 SKU by quantity", "last20": "Last 20 orders",
        "col_order": "Order", "col_date": "Date", "col_status": "Status",
        "col_market": "Market", "col_sum": "Total",
        "no_orders": "No orders for selected period.",
        "search": "Search SKU / ASIN / name (comma-separated for multiple)", "sku_in_stock": "SKUs in stock > 0",
        "total_rows": "total rows", "inbound_sub": "working + shipped + receiving",
        "top15_sku": "Top-15 SKU by fulfillable", "stock_by_sku": "Stock by SKU",
        "snapshot": "snapshot", "col_name": "Product name", "col_photo": "Photo",
        "col_qty": "Qty",
        "no_inventory": "No data in fba_inventory — run 02_fba_inventory_loader.py",
        "legend_stock": "🔴 fulfillable = 0 · 🟡 fulfillable < 20",
        "cache_note": "Data from merinoprotect · cache 10 min",
        "sort_by": "Sort by", "sort_asc": "Ascending", "sort_desc": "Descending",
        "sort_order_label": "Order",
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
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("logo.png", "Logo.png", "logo.PNG",
                 os.path.join("assets", "logo.png")):
        p = os.path.join(here, name)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None


def lang_selector() -> str:
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
        st.page_link("app.py", label=t("nav_overview"), icon=":material/bar_chart:")
        st.page_link("pages/1_Stock.py", label=t("nav_stock"), icon=":material/inventory_2:")
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
            if st.button("Dark", key="th_dark", use_container_width=True,
                         icon=":material/dark_mode:",
                         type="primary" if st.session_state["theme"] == "dark" else "secondary"):
                st.session_state["theme"] = "dark"
                st.rerun()
        with tc2:
            if st.button("Light", key="th_light", use_container_width=True,
                         icon=":material/light_mode:",
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
    conn = psycopg2.connect(_database_url(), connect_timeout=10)
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

.stApp {{ background: {th["bg"]} !important; }}
[data-testid="stSidebar"] {{ background: {th["sidebar"]} !important; }}
.stApp, .stApp p, .stApp span, .stApp label,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: {th["text"]} !important; }}
.stCaption, .stApp small {{ color: {th["muted"]} !important; }}

.mp-logo {{ filter: {th["logo_filter"]}; }}

.block-container {{ padding-top: 1.6rem; padding-bottom: 2rem; }}
header[data-testid="stHeader"] {{ background: transparent; }}

div[data-baseweb="select"] > div,
div[data-baseweb="select"] div,
[data-testid="stSelectbox"] * {{
    background-color: {th["card"]} !important;
    color: {th["text"]} !important;
    border-color: {th["border"]} !important;
}}
ul[role="listbox"], div[data-baseweb="popover"], div[data-baseweb="menu"] {{
    background-color: {th["card"]} !important;
}}
li[role="option"], li[role="option"] * {{
    background-color: {th["card"]} !important;
    color: {th["text"]} !important;
}}
li[role="option"]:hover {{ background-color: {th["border"]} !important; }}

[data-testid="stTextInput"] input {{
    background-color: {th["card"]} !important;
    color: {th["text"]} !important;
    border-color: {th["border"]} !important;
}}

button[kind="secondary"], button[kind="secondary"] * {{
    background-color: {th["card"]} !important;
    color: {th["text"]} !important;
    border-color: {th["border"]} !important;
}}
button[kind="secondary"]:hover {{ border-color: {ACCENT} !important; }}

[data-testid="stPageLink"] * {{ color: {th["text"]} !important; }}

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

.mp-table-wrap {{
    overflow-y: auto;
    border: 1px solid {th["border"]};
    border-radius: 10px;
    background: {th["card"]};
}}
.mp-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.mp-table thead th {{
    position: sticky;
    top: 0;
    background: {th["card"]};
    color: {th["muted"]};
    text-align: left;
    padding: 9px 12px;
    border-bottom: 1px solid {th["border"]};
    font-weight: 600;
    z-index: 1;
    white-space: nowrap;
}}
.mp-table tbody td {{
    padding: 7px 12px;
    border-bottom: 1px solid {th["border"]};
    color: {th["text"]};
    vertical-align: middle;
}}
.mp-table tbody tr:hover {{ background: {th["row_hover"]}; }}
.mp-table tbody tr.row-zero {{ background: rgba(239,68,68,0.14); }}
.mp-table tbody tr.row-low {{ background: rgba(245,158,11,0.12); }}
.mp-table a {{ color: {ACCENT2}; text-decoration: none; font-weight: 500; }}
.mp-table a:hover {{ text-decoration: underline; }}
.mp-table img.mp-thumb {{
    width: 34px; height: 34px; object-fit: cover; border-radius: 6px;
    background: rgba(128,128,128,0.15); display: block;
}}
.mp-thumb-empty {{
    width: 34px; height: 34px; border-radius: 6px;
    background: rgba(128,128,128,0.15); display: block;
}}

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


# ------------------------------------------------------ HTML-таблиці ----

def cell_photo(url) -> str:
    if url and isinstance(url, str) and url.strip():
        return (f'<img class="mp-thumb" src="{url}" '
                f'onerror="this.outerHTML=\'<div class=mp-thumb-empty></div>\'">')
    return '<div class="mp-thumb-empty"></div>'


def cell_link(url, text) -> str:
    if not url or not text:
        return str(text or "")
    return f'<a href="{url}" target="_blank">{text}</a>'


def render_html_table(rows, columns, height=420):
    parts = [f'<div class="mp-table-wrap" style="max-height:{height}px;">',
             '<table class="mp-table"><thead><tr>']
    for label, _ in columns:
        parts.append(f"<th>{label}</th>")
    parts.append("</tr></thead><tbody>")
    for row in rows:
        row_cls = row.get("_row_class", "") if isinstance(row, dict) else ""
        parts.append(f'<tr class="{row_cls}">')
        for _, render_fn in columns:
            parts.append(f"<td>{render_fn(row)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def sort_controls(options: dict, key: str, default_index: int = 0,
                  default_desc: bool = True):
    """Компактний рядок керування сортуванням (одна строка, малий шрифт)."""
    labels = list(options.keys())
    th = cur_theme()
    c1, c2 = st.columns([2, 2])
    with c1:
        sel = st.selectbox(t("sort_by"), labels, index=default_index,
                           key=f"sort_col_{key}")
    with c2:
        order = st.selectbox(t("sort_order_label"), [t("sort_desc"), t("sort_asc")],
                             index=0 if default_desc else 1,
                             key=f"sort_ord_{key}")
    ascending = order == t("sort_asc")
    return options[sel], ascending
