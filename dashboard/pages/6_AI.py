# -*- coding: utf-8 -*-
"""Merinnovation Dashboard — висновки ІІ-аналітика."""

import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (ACCENT, cur_theme, inject_css, lang_selector, q, t)

st.set_page_config(layout="wide", page_title="Merinnovation · AI", page_icon="🐑")
lang_selector()
inject_css()

st.markdown(f"## {t('ai_title')}")

# ------------------------------------------------- перевірка таблиці ----
exists = q("""
    SELECT COUNT(*) AS n
    FROM information_schema.tables
    WHERE table_schema = 'merinnovation' AND table_name = 'ai_insights'
""")
if exists.empty or int(exists["n"].iloc[0]) == 0:
    st.info(t("no_ai_data"))
    st.stop()

# ------------------------------------------------------------- дані ----
dates = q("""
    SELECT DISTINCT report_date
    FROM merinnovation.ai_insights
    ORDER BY report_date DESC LIMIT 30
""")
if dates.empty:
    st.info(t("no_ai_data"))
    st.stop()

date_options = pd.to_datetime(dates["report_date"]).dt.date.tolist()

fc1, _ = st.columns([2, 6])
with fc1:
    sel_date = st.selectbox(
        t("ai_report_date"), date_options,
        format_func=lambda d: d.strftime("%d.%m.%Y"), key="ai_date")

insights = q("""
    SELECT DISTINCT ON (agent) agent, title, content, model, created_at
    FROM merinnovation.ai_insights
    WHERE report_date = %s
    ORDER BY agent, created_at DESC
""", (sel_date,))

if insights.empty:
    st.info(t("no_ai_data"))
    st.stop()

th = cur_theme()

AGENT_ICONS = {
    "main": "🧠", "sales": "📈", "stock": "📦",
    "forecast": "🔮", "finance": "💰", "traffic": "🔍",
}
AGENT_ORDER = ["main", "sales", "stock", "forecast", "finance", "traffic"]


def card(title: str, body: str, accent: bool = False):
    border = ACCENT if accent else th["border"]
    bg = th["card"]
    safe = (body or "").replace("<", "&lt;").replace(">", "&gt;")
    safe = safe.replace("\n", "<br>")
    st.markdown(
        f'<div style="background:{bg};border:1px solid {border};'
        f'border-left:3px solid {ACCENT if accent else border};'
        f'border-radius:12px;padding:18px 20px;margin-bottom:14px;">'
        f'<div style="color:{th["muted"]};font-size:13px;margin-bottom:10px;'
        f'text-transform:uppercase;letter-spacing:.04em;">{title}</div>'
        f'<div style="color:{th["text"]};font-size:15px;line-height:1.65;">'
        f'{safe}</div></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------- головна сводка ----
main = insights[insights["agent"] == "main"]
if not main.empty:
    r = main.iloc[0]
    card(f"{AGENT_ICONS['main']} {r['title']}", r["content"], accent=True)
    st.caption(f"{t('ai_model')}: {r['model']} · "
               f"{pd.to_datetime(r['created_at']):%d.%m.%Y %H:%M}")
    st.markdown("")

# ------------------------------------------------ висновки агентів ----
others = insights[insights["agent"] != "main"].copy()
if not others.empty:
    st.markdown(f"**{t('ai_by_agent')}**")

    others["order"] = others["agent"].apply(
        lambda a: AGENT_ORDER.index(a) if a in AGENT_ORDER else 99)
    others = others.sort_values("order")

    records = others.to_dict("records")
    for i in range(0, len(records), 2):
        cols = st.columns(2)
        for col, rec in zip(cols, records[i:i + 2]):
            with col:
                icon = AGENT_ICONS.get(rec["agent"], "•")
                card(f"{icon} {rec['title']}", rec["content"])

# ----------------------------------------------------------- історія ----
st.markdown("")
with st.expander(t("ai_history")):
    hist = q("""
        SELECT report_date, content, created_at
        FROM merinnovation.ai_insights
        WHERE agent = 'main'
        ORDER BY created_at DESC LIMIT 14
    """)
    if hist.empty:
        st.caption(t("no_ai_data"))
    else:
        for _, r in hist.iterrows():
            d = pd.to_datetime(r["report_date"]).strftime("%d.%m.%Y")
            st.markdown(f"**{d}**")
            st.markdown(r["content"])
            st.markdown("---")

st.caption(t("ai_cache_note"))
