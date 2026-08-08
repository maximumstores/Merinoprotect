# -*- coding: utf-8 -*-
"""Merinnovation Dashboard — ІІ-аналітик у форматі консалтингового звіту."""

import json
import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (ACCENT, ACCENT2, cur_theme, inject_css, lang_selector,
                metric_card, plotly_layout, q, t, themed_axis)

st.set_page_config(layout="wide", page_title="Merinnovation · AI", page_icon="🐑")
lang_selector()
inject_css()

th = cur_theme()

SEV = {
    "critical": ("#ef4444", "🔴"),
    "warning": ("#f59e0b", "🟠"),
    "ok": (ACCENT, "🟢"),
}
AGENT_ICONS = {"main": "🧠", "sales": "📈", "stock": "📦",
               "forecast": "🔮", "finance": "💰", "traffic": "🔍"}
AGENT_ORDER = ["main", "sales", "stock", "forecast", "finance", "traffic"]

st.markdown(f"## {t('ai_title')}")

# ------------------------------------------------- перевірка таблиці ----
exists = q("""
    SELECT COUNT(*) AS n FROM information_schema.tables
    WHERE table_schema='merinnovation' AND table_name='ai_insights'
""")
if exists.empty or int(exists["n"].iloc[0]) == 0:
    st.info(t("no_ai_data"))
    st.stop()

dates = q("""
    SELECT DISTINCT report_date FROM merinnovation.ai_insights
    ORDER BY report_date DESC LIMIT 30
""")
if dates.empty:
    st.info(t("no_ai_data"))
    st.stop()

date_options = pd.to_datetime(dates["report_date"]).dt.date.tolist()
fc1, _ = st.columns([2, 6])
with fc1:
    sel_date = st.selectbox(t("ai_report_date"), date_options,
                            format_func=lambda d: d.strftime("%d.%m.%Y"),
                            key="ai_date")

insights = q("""
    SELECT DISTINCT ON (agent) agent, title, content, structured, model, created_at
    FROM merinnovation.ai_insights
    WHERE report_date = %s
    ORDER BY agent, created_at DESC
""", (sel_date,))

if insights.empty:
    st.info(t("no_ai_data"))
    st.stop()


def parsed_of(row) -> dict:
    """structured може прийти як dict, як рядок JSON, або бути порожнім."""
    s = row.get("structured")
    if isinstance(s, dict):
        return s
    if isinstance(s, str) and s.strip():
        try:
            return json.loads(s)
        except Exception:
            pass
    return {"headline": (row.get("content") or "")[:400],
            "severity": "ok", "findings": [], "actions": []}


# ============================================================ рендер ----

def render_headline(d: dict, title: str, icon: str):
    color, sev_icon = SEV.get(d.get("severity", "ok"), SEV["ok"])
    head = (d.get("headline") or "").replace("<", "&lt;")
    st.markdown(
        f'<div style="background:{th["card"]};border:1px solid {th["border"]};'
        f'border-left:4px solid {color};border-radius:14px;'
        f'padding:22px 26px;margin-bottom:18px;">'
        f'<div style="color:{th["muted"]};font-size:12px;letter-spacing:.08em;'
        f'text-transform:uppercase;margin-bottom:12px;">{icon} {title}</div>'
        f'<div style="color:{th["text"]};font-size:22px;font-weight:600;'
        f'line-height:1.4;">{sev_icon} {head}</div></div>',
        unsafe_allow_html=True)


def render_findings(d: dict):
    findings = d.get("findings") or []
    if not findings:
        return
    rows = []
    for f in findings:
        arrow = {"up": "▲", "down": "▼"}.get(f.get("direction"), "•")
        a_color = {"up": ACCENT, "down": "#ef4444"}.get(
            f.get("direction"), th["muted"])
        text = (f.get("text") or "").replace("<", "&lt;")
        metric = (f.get("metric") or "").replace("<", "&lt;")
        metric_html = (
            f'<span style="color:{a_color};font-weight:700;font-size:15px;'
            f'white-space:nowrap;margin-left:14px;">{metric}</span>'
            if metric else "")
        rows.append(
            f'<div style="display:flex;align-items:flex-start;'
            f'justify-content:space-between;gap:12px;padding:11px 0;'
            f'border-bottom:1px solid {th["border"]};">'
            f'<div style="color:{th["text"]};font-size:14px;line-height:1.55;">'
            f'<span style="color:{a_color};margin-right:8px;">{arrow}</span>'
            f'{text}</div>{metric_html}</div>')
    st.markdown(
        f'<div style="background:{th["card"]};border:1px solid {th["border"]};'
        f'border-radius:12px;padding:6px 20px 10px 20px;margin-bottom:14px;">'
        f'{"".join(rows)}</div>', unsafe_allow_html=True)


def render_actions(d: dict):
    actions = d.get("actions") or []
    if not actions:
        return
    items = "".join(
        f'<div style="padding:9px 0;color:{th["text"]};font-size:14px;">'
        f'<span style="color:{ACCENT};font-weight:700;margin-right:10px;">→</span>'
        f'{str(a).replace("<", "&lt;")}</div>' for a in actions)
    st.markdown(
        f'<div style="background:{th["card"]};'
        f'border:1px solid {ACCENT}55;border-radius:12px;'
        f'padding:14px 20px;margin-bottom:18px;">'
        f'<div style="color:{ACCENT};font-size:12px;letter-spacing:.08em;'
        f'text-transform:uppercase;margin-bottom:6px;font-weight:700;">'
        f'{t("ai_actions")}</div>{items}</div>', unsafe_allow_html=True)


# ================================================== головна сводка ----
main_row = insights[insights["agent"] == "main"]
if not main_row.empty:
    r = main_row.iloc[0]
    d = parsed_of(r)
    render_headline(d, t("ai_main_summary"), AGENT_ICONS["main"])
    render_findings(d)
    render_actions(d)
    st.caption(f"{t('ai_model')}: {r['model']} · "
               f"{pd.to_datetime(r['created_at']):%d.%m.%Y %H:%M}")

st.markdown("---")

# ================================================ опорні показники ----
st.markdown(f"**{t('ai_supporting_data')}**")

kpi = q("""
    SELECT
      (SELECT COUNT(*) FROM merinnovation.orders
        WHERE purchase_date >= NOW() - INTERVAL '7 days'
          AND order_status <> 'Canceled') AS orders_7d,
      (SELECT COUNT(*) FROM merinnovation.orders
        WHERE purchase_date >= NOW() - INTERVAL '14 days'
          AND purchase_date < NOW() - INTERVAL '7 days'
          AND order_status <> 'Canceled') AS orders_prev_7d,
      (SELECT COUNT(*) FROM merinnovation.forecast_sku
        WHERE velocity_weighted > 0 AND fulfillable = 0) AS stockouts,
      (SELECT COUNT(*) FROM merinnovation.forecast_sku
        WHERE status = 'REORDER_NOW') AS reorder_now,
      (SELECT COALESCE(SUM(recommended_qty), 0) FROM merinnovation.forecast_sku
        WHERE status IN ('REORDER_NOW','OUT_OF_STOCK')) AS units_to_order
""")

if not kpi.empty:
    k = kpi.iloc[0]
    o7, op7 = int(k["orders_7d"] or 0), int(k["orders_prev_7d"] or 0)
    delta = (f"{abs((o7 - op7) / op7 * 100):.0f}%" if op7 else None)
    up = o7 >= op7

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(t("ai_orders_7d"), f"{o7:,}", delta=delta, delta_up=up,
                    sub=f"{t('ai_prev')}: {op7:,}")
    with c2:
        metric_card(t("ai_stockouts"), f"{int(k['stockouts'] or 0)}",
                    sub=t("ai_stockouts_sub"))
    with c3:
        metric_card(t("ai_reorder_now"), f"{int(k['reorder_now'] or 0)}")
    with c4:
        metric_card(t("ai_units_to_order"), f"{int(k['units_to_order'] or 0):,}")

# графік динаміки замовлень
daily = q("""
    SELECT purchase_date::date AS day, COUNT(*) AS orders
    FROM merinnovation.orders
    WHERE purchase_date >= NOW() - INTERVAL '30 days'
      AND order_status <> 'Canceled'
    GROUP BY 1 ORDER BY 1
""")
if not daily.empty:
    daily["label"] = pd.to_datetime(daily["day"]).dt.strftime("%d.%m")
    fig = go.Figure(go.Bar(x=daily["label"], y=daily["orders"],
                           marker_color=ACCENT))
    lk = plotly_layout(title=t("ai_orders_chart"))
    lk["height"] = 260
    lk["xaxis"] = themed_axis(type="category", showgrid=False)
    fig.update_layout(**lk)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ================================================== ДЕ ТЕЧУТЬ ГРОШІ ----
leaks_exist = q("""
    SELECT COUNT(*) AS n FROM information_schema.tables
    WHERE table_schema='merinnovation' AND table_name='money_leaks'
""")
has_leaks = not leaks_exist.empty and int(leaks_exist["n"].iloc[0]) > 0

if has_leaks:
    by_type = q("""
        SELECT category, leak_type, COUNT(*) AS sku_count, SUM(amount_usd) AS usd
        FROM merinnovation.money_leaks
        GROUP BY 1, 2 ORDER BY 4 DESC
    """)

    if not by_type.empty:
        lost = by_type[by_type["category"] == "lost_revenue"]
        frozen = by_type[by_type["category"] == "frozen_capital"]
        total_lost = float(lost["usd"].sum()) if not lost.empty else 0.0
        total_frozen = float(frozen["usd"].sum()) if not frozen.empty else 0.0

        LEAK_LABELS = {
            "STOCKOUT_NOW": t("leak_stockout_now"),
            "STOCKOUT_SOON": t("leak_stockout_soon"),
            "CONVERSION_GAP": t("leak_conversion"),
            "REFUNDS": t("leak_refunds"),
            "FEE_BURDEN": t("leak_fees"),
            "DEAD_STOCK": t("leak_dead_stock"),
        }

        # дві картки: втрачене і заморожене — принципово різні речі
        hl, hr = st.columns([1, 1])
        with hl:
            st.markdown(
                f'<div style="background:{th["card"]};'
                f'border:1px solid #ef444455;border-left:4px solid #ef4444;'
                f'border-radius:14px;padding:20px 24px;height:100%;">'
                f'<div style="color:{th["muted"]};font-size:12px;'
                f'letter-spacing:.08em;text-transform:uppercase;'
                f'margin-bottom:8px;">💸 {t("leaks_lost_title")}</div>'
                f'<div style="color:#ef4444;font-size:32px;font-weight:800;'
                f'line-height:1.1;">${total_lost:,.0f}</div>'
                f'<div style="color:{th["muted"]};font-size:12px;'
                f'margin-top:6px;">{t("leaks_lost_note")}</div></div>',
                unsafe_allow_html=True)
        with hr:
            st.markdown(
                f'<div style="background:{th["card"]};'
                f'border:1px solid {ACCENT2}55;border-left:4px solid {ACCENT2};'
                f'border-radius:14px;padding:20px 24px;height:100%;">'
                f'<div style="color:{th["muted"]};font-size:12px;'
                f'letter-spacing:.08em;text-transform:uppercase;'
                f'margin-bottom:8px;">🧊 {t("leaks_frozen_title")}</div>'
                f'<div style="color:{ACCENT2};font-size:32px;font-weight:800;'
                f'line-height:1.1;">${total_frozen:,.0f}</div>'
                f'<div style="color:{th["muted"]};font-size:12px;'
                f'margin-top:6px;">{t("leaks_frozen_note")}</div></div>',
                unsafe_allow_html=True)

        st.markdown("")

        # розбивка втрат за типом
        if not lost.empty:
            lc, rc = st.columns([1, 1])
            with lc:
                b = lost.copy()
                b["label"] = b["leak_type"].map(lambda x: LEAK_LABELS.get(x, x))
                b = b.sort_values("usd")
                figl = go.Figure(go.Bar(
                    x=b["usd"], y=b["label"], orientation="h",
                    marker_color="#ef4444",
                    text=[f"${v:,.0f}" for v in b["usd"]],
                    textposition="outside"))
                lk = plotly_layout(title=t("leaks_by_type"))
                lk["height"] = 280
                lk["yaxis"] = themed_axis(type="category")
                figl.update_layout(**lk)
                st.plotly_chart(figl, use_container_width=True)

            with rc:
                rows = []
                for _, r in lost.sort_values("usd", ascending=False).iterrows():
                    label = LEAK_LABELS.get(r["leak_type"], r["leak_type"])
                    share = (float(r["usd"]) / total_lost * 100
                             if total_lost else 0)
                    rows.append(
                        f'<div style="padding:12px 0;border-bottom:1px solid '
                        f'{th["border"]};">'
                        f'<div style="display:flex;justify-content:space-between;'
                        f'align-items:baseline;">'
                        f'<span style="color:{th["text"]};font-size:14px;">'
                        f'{label}</span>'
                        f'<span style="color:#ef4444;font-weight:700;'
                        f'font-size:16px;white-space:nowrap;margin-left:12px;">'
                        f'${float(r["usd"]):,.0f}</span></div>'
                        f'<div style="color:{th["muted"]};font-size:12px;'
                        f'margin-top:3px;">{int(r["sku_count"])} SKU · '
                        f'{share:.0f}% {t("leaks_of_total")}</div></div>')
                st.markdown(
                    f'<div style="background:{th["card"]};'
                    f'border:1px solid {th["border"]};border-radius:12px;'
                    f'padding:4px 20px 8px 20px;">{"".join(rows)}</div>',
                    unsafe_allow_html=True)

        # топ саме втрат — список для дії
        st.markdown("")
        st.markdown(f"**{t('leaks_top_positions')}**")

        top_leaks = q("""
            SELECT leak_type, seller_sku, asin, amount_usd, detail
            FROM merinnovation.money_leaks
            WHERE category = 'lost_revenue'
            ORDER BY amount_usd DESC LIMIT 15
        """)

        if top_leaks.empty:
            st.caption(t("leaks_none"))
        else:
            items = []
            for _, r in top_leaks.iterrows():
                det = r["detail"]
                if isinstance(det, str):
                    try:
                        det = json.loads(det)
                    except Exception:
                        det = {}
                det = det or {}
                reason = str(det.get("reason", "")).replace("<", "&lt;")
                label = LEAK_LABELS.get(r["leak_type"], r["leak_type"])
                sku = str(r["seller_sku"] or "")[:32]
                items.append(
                    f'<div style="padding:13px 0;border-bottom:1px solid '
                    f'{th["border"]};">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:baseline;gap:12px;">'
                    f'<span style="color:{th["text"]};font-weight:600;'
                    f'font-size:14px;">{sku}</span>'
                    f'<span style="color:#ef4444;font-weight:700;'
                    f'white-space:nowrap;">${float(r["amount_usd"]):,.0f}</span>'
                    f'</div>'
                    f'<div style="color:{th["muted"]};font-size:12px;'
                    f'margin-top:4px;">{label} · {reason}</div></div>')
            st.markdown(
                f'<div style="background:{th["card"]};'
                f'border:1px solid {th["border"]};border-radius:12px;'
                f'padding:4px 20px 8px 20px;">{"".join(items)}</div>',
                unsafe_allow_html=True)

    st.markdown("---")

# ============================================== розділи за напрямами ----
others = insights[insights["agent"] != "main"].copy()
if not others.empty:
    others["order"] = others["agent"].apply(
        lambda a: AGENT_ORDER.index(a) if a in AGENT_ORDER else 99)
    others = others.sort_values("order")

    for _, row in others.iterrows():
        d = parsed_of(row)
        icon = AGENT_ICONS.get(row["agent"], "•")
        render_headline(d, row["title"], icon)
        render_findings(d)
        render_actions(d)

# ----------------------------------------------------------- історія ----
with st.expander(t("ai_history")):
    hist = q("""
        SELECT report_date, structured, content
        FROM merinnovation.ai_insights
        WHERE agent = 'main'
        ORDER BY created_at DESC LIMIT 14
    """)
    if hist.empty:
        st.caption(t("no_ai_data"))
    else:
        for _, r in hist.iterrows():
            d = parsed_of(r)
            day = pd.to_datetime(r["report_date"]).strftime("%d.%m.%Y")
            _, sev_icon = SEV.get(d.get("severity", "ok"), SEV["ok"])
            st.markdown(f"**{day}** {sev_icon} {d.get('headline', '')}")
            for f in (d.get("findings") or [])[:3]:
                st.caption(f"· {f.get('text', '')}")
            st.markdown("---")

st.caption(t("ai_cache_note"))
