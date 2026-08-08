# -*- coding: utf-8 -*-
"""Merinnovation Dashboard — монітор запитів на відгуки (Request a Review)."""

import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (ACCENT, ACCENT2, AMAZON_DOMAINS, cell_link, cell_photo,
                download_csv_button, inject_css, lang_selector, metric_card,
                mp_label, plotly_layout, q, render_html_table, sort_controls,
                t, themed_axis)

st.set_page_config(layout="wide", page_title="Merinnovation · Reviews",
                   page_icon="🐑")
lang_selector()
inject_css()

# Вікно відправки: лоадер бере замовлення 8-33 днів від дати замовлення
AGE_MIN, AGE_MAX = 8, 33

st.markdown(f"## {t('reviews_title')}")

# ------------------------------------------------------------ health ----
kpi = q("""
    SELECT
      COUNT(*) FILTER (WHERE status='sent' AND sent_at::date = CURRENT_DATE) AS today,
      COUNT(*) FILTER (WHERE status='sent' AND sent_at >= NOW() - INTERVAL '7 days') AS sent7,
      COUNT(*) FILTER (WHERE status LIKE 'failed%' AND sent_at >= NOW() - INTERVAL '7 days') AS failed7,
      MAX(sent_at) FILTER (WHERE status='sent') AS last_sent,
      COUNT(*) AS total_rows
    FROM merinnovation.review_requests
""")

if kpi.empty or int(kpi["total_rows"].iloc[0] or 0) == 0:
    st.info(t("no_reviews_data"))
    st.stop()

k = kpi.iloc[0]
last_sent = pd.to_datetime(k["last_sent"]) if pd.notna(k["last_sent"]) else None
hours_since = ((datetime.now(last_sent.tzinfo) - last_sent).total_seconds() / 3600
               if last_sent is not None else None)

if hours_since is not None and hours_since > 25:
    st.error(t("health_warn").format(h=hours_since))
else:
    st.success(t("health_ok"))

# --------------------------------------------------------------- пул ----
pool = q(f"""
    SELECT
      COUNT(*) FILTER (WHERE o.purchase_date >= NOW() - INTERVAL '15 days') AS fresh,
      COUNT(*) FILTER (WHERE o.purchase_date <  NOW() - INTERVAL '15 days'
                         AND o.purchase_date >= NOW() - INTERVAL '25 days') AS mid,
      COUNT(*) FILTER (WHERE o.purchase_date <  NOW() - INTERVAL '25 days') AS burning,
      COUNT(*) AS pool_total
    FROM merinnovation.orders o
    WHERE o.order_status = 'Shipped'
      AND o.purchase_date BETWEEN NOW() - INTERVAL '{AGE_MAX} days'
                              AND NOW() - INTERVAL '{AGE_MIN} days'
      AND NOT EXISTS (
          SELECT 1 FROM merinnovation.review_requests r
          WHERE r.order_id = o.amazon_order_id
            AND r.status IN ('sent','already')
      )
""")
p = pool.iloc[0] if not pool.empty else {}

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(t("sent_today"), f"{int(k['today'] or 0):,}",
                sub=f"{t('sent_7d')}: {int(k['sent7'] or 0):,}")
with c2:
    metric_card(t("pool_label"), f"{int(p.get('pool_total', 0) or 0):,}",
                sub=t("pool_sub"))
with c3:
    metric_card(t("burning_label"), f"{int(p.get('burning', 0) or 0):,}")
with c4:
    metric_card(t("failed_7d"), f"{int(k['failed7'] or 0):,}",
                sub=(last_sent.strftime("%d.%m %H:%M") if last_sent is not None
                     else "—"))

st.markdown("")

# ------------------------------------------------- обсяг по днях ----
daily = q("""
    SELECT sent_at::date AS day,
           COUNT(*) FILTER (WHERE status='sent') AS sent,
           COUNT(*) FILTER (WHERE status='already') AS already,
           COUNT(*) FILTER (WHERE status='outside') AS outside,
           COUNT(*) FILTER (WHERE status LIKE 'failed%') AS failed
    FROM merinnovation.review_requests
    WHERE sent_at >= NOW() - INTERVAL '30 days'
    GROUP BY 1 ORDER BY 1
""")

if not daily.empty:
    daily["label"] = pd.to_datetime(daily["day"]).dt.strftime("%d.%m")
    fig = go.Figure()
    fig.add_bar(x=daily["label"], y=daily["sent"], name=t("st_sent"),
                marker_color=ACCENT)
    fig.add_bar(x=daily["label"], y=daily["already"], name=t("st_already"),
                marker_color=ACCENT2)
    fig.add_bar(x=daily["label"], y=daily["outside"], name=t("st_outside"),
                marker_color="#f59e0b")
    fig.add_bar(x=daily["label"], y=daily["failed"], name=t("st_failed"),
                marker_color="#ef4444")
    lk = plotly_layout(title=t("daily_volume"))
    lk["barmode"] = "stack"
    lk["xaxis"] = themed_axis(type="category", showgrid=False)
    fig.update_layout(**lk)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("status_hint"))

# ------------------------------------------------ пул за терміновістю ----
gl, gr = st.columns(2)

with gl:
    buckets = pd.DataFrame({
        "b": [t("pool_fresh"), t("pool_mid"), t("pool_burning")],
        "n": [int(p.get("fresh", 0) or 0), int(p.get("mid", 0) or 0),
              int(p.get("burning", 0) or 0)],
    })
    figp = go.Figure(go.Bar(
        x=buckets["n"], y=buckets["b"], orientation="h",
        marker_color=[ACCENT, "#f59e0b", "#ef4444"],
        text=buckets["n"], textposition="outside"))
    lk = plotly_layout(title=t("pool_title"))
    lk["height"] = 280
    lk["yaxis"] = themed_axis(autorange="reversed")
    figp.update_layout(**lk)
    st.plotly_chart(figp, use_container_width=True)

with gr:
    funnel = q(f"""
        SELECT
          (SELECT COUNT(*) FROM merinnovation.orders
            WHERE order_status='Shipped'
              AND purchase_date >= NOW() - INTERVAL '30 days') AS orders30,
          (SELECT COUNT(*) FROM merinnovation.review_requests
            WHERE status='sent' AND sent_at >= NOW() - INTERVAL '30 days') AS sent30
    """)
    f = funnel.iloc[0] if not funnel.empty else {}
    figf = go.Figure(go.Funnel(
        y=[t("f_orders"), t("f_pool"), t("f_sent")],
        x=[int(f.get("orders30", 0) or 0), int(p.get("pool_total", 0) or 0),
           int(f.get("sent30", 0) or 0)],
        textinfo="value+percent initial",
        marker=dict(color=[ACCENT2, "#f59e0b", ACCENT])))
    lk = plotly_layout(title=t("funnel_title"))
    lk["height"] = 280
    figf.update_layout(**lk)
    st.plotly_chart(figf, use_container_width=True)

# ------------------------------------------- покриття по датах ----
st.markdown(f"**{t('coverage_title')}**")
st.caption(t("coverage_note"))

cov = q(f"""
    WITH ord AS (
        SELECT purchase_date::date AS day,
               COUNT(DISTINCT amazon_order_id) AS orders
        FROM merinnovation.orders
        WHERE order_status = 'Shipped'
          AND purchase_date >= NOW() - INTERVAL '45 days'
        GROUP BY 1
    ), req AS (
        SELECT o.purchase_date::date AS day,
               COUNT(DISTINCT r.order_id) FILTER (WHERE r.status='sent') AS sent,
               COUNT(DISTINCT r.order_id) FILTER (WHERE r.status='already') AS already,
               COUNT(DISTINCT r.order_id) FILTER (WHERE r.status LIKE 'failed%') AS errors
        FROM merinnovation.review_requests r
        JOIN merinnovation.orders o ON o.amazon_order_id = r.order_id
        WHERE o.purchase_date >= NOW() - INTERVAL '45 days'
        GROUP BY 1
    )
    SELECT ord.day, ord.orders,
           COALESCE(req.sent,0) AS sent,
           COALESCE(req.already,0) AS already,
           COALESCE(req.errors,0) AS errors
    FROM ord LEFT JOIN req USING (day)
    ORDER BY ord.day DESC
""")

if not cov.empty:
    cov["covered"] = cov["sent"] + cov["already"]
    cov["unprocessed"] = (cov["orders"] - cov["covered"]).clip(lower=0)
    cov["coverage"] = (cov["covered"] / cov["orders"].replace(0, pd.NA) * 100).round(1)
    today = pd.Timestamp(datetime.now().date())
    cov["age"] = (today - pd.to_datetime(cov["day"])).dt.days

    def status_of(r):
        if r["age"] < AGE_MIN:
            return "maturing"
        if pd.isna(r["coverage"]):
            return "none"
        if r["coverage"] >= 90:
            return "ok"
        return "progress" if r["age"] <= AGE_MAX else "missed"

    cov["st"] = cov.apply(status_of, axis=1)

    ST_LABEL = {
        "ok": "🟢 " + t("st_ok"), "progress": "🟠 " + t("st_progress"),
        "missed": "🔴 " + t("st_missed"), "maturing": "⏳ " + t("st_maturing"),
        "none": "⚪ —",
    }
    ST_CLASS = {"missed": "row-zero", "progress": "row-low"}

    matured = cov[cov["st"] != "maturing"]
    t_orders = int(matured["orders"].sum())
    t_cov = round(matured["covered"].sum() / t_orders * 100, 1) if t_orders else 0
    t_missed = int(cov.loc[cov["st"] == "missed", "unprocessed"].sum())

    m1, m2, m3 = st.columns(3)
    with m1:
        metric_card(t("cov_orders"), f"{t_orders:,}", sub=t("matured_only"))
    with m2:
        metric_card(t("cov_pct"), f"{t_cov:.1f}%")
    with m3:
        metric_card(t("missed_total"), f"{t_missed:,}", sub=t("missed_sub"))

    rows = []
    for rec in cov.to_dict("records"):
        rec["_row_class"] = ST_CLASS.get(rec["st"], "")
        rec["day_label"] = pd.to_datetime(rec["day"]).strftime("%d.%m.%Y")
        rec["st_label"] = ST_LABEL.get(rec["st"], "")
        rec["cov_label"] = ("—" if pd.isna(rec["coverage"])
                            else f"{rec['coverage']:.0f}%")
        rows.append(rec)

    columns = [
        (t("col_date"), lambda r: r.get("day_label") or ""),
        (t("cov_orders"), lambda r: str(int(r.get("orders", 0)))),
        (t("st_sent"), lambda r: str(int(r.get("sent", 0)))),
        (t("st_already"), lambda r: str(int(r.get("already", 0)))),
        (t("cov_pct"), lambda r: r.get("cov_label") or ""),
        (t("cov_unprocessed"), lambda r: str(int(r.get("unprocessed", 0)))),
        (t("col_status"), lambda r: r.get("st_label") or ""),
    ]
    render_html_table(rows, columns, height=420)
    download_csv_button(
        cov[["day", "orders", "sent", "already", "errors", "coverage",
             "unprocessed", "st"]],
        "review_coverage", key="reviews_cov")
    st.caption(t("coverage_legend"))

# ---------------------------------------------------------- по ASIN ----
st.markdown("")
st.markdown(f"**{t('by_asin_title')}**")

by_asin = q("""
    SELECT oi.asin,
           COUNT(DISTINCT r.order_id) FILTER (WHERE r.status='sent') AS sent,
           COUNT(DISTINCT r.order_id) FILTER (WHERE r.status='already') AS already,
           COUNT(DISTINCT r.order_id) FILTER (WHERE r.status='outside') AS outside,
           MAX(o.marketplace_id) AS marketplace_id,
           MAX(c.image_url) AS image_url
    FROM merinnovation.review_requests r
    JOIN merinnovation.orders o ON o.amazon_order_id = r.order_id
    JOIN merinnovation.order_items oi USING (amazon_order_id)
    LEFT JOIN merinnovation.catalog_images c
      ON c.asin = oi.asin AND c.marketplace_id = o.marketplace_id
    WHERE r.sent_at >= NOW() - INTERVAL '30 days'
      AND oi.asin IS NOT NULL
    GROUP BY oi.asin
    ORDER BY sent DESC
""")

if by_asin.empty:
    st.info(t("no_asin_data"))
else:
    by_asin["asin_link"] = (
        "https://" + by_asin["marketplace_id"].map(AMAZON_DOMAINS).fillna("amazon.com")
        + "/dp/" + by_asin["asin"].fillna(""))

    st.caption(t("sort_hint"))
    sort_col, sort_asc = sort_controls(
        {t("st_sent"): "sent", t("st_already"): "already", "ASIN": "asin"},
        key="reviews_asin", default_index=0, default_desc=True)
    by_asin = by_asin.sort_values(sort_col, ascending=sort_asc)

    columns_a = [
        ("", lambda r: cell_photo(r.get("image_url"))),
        ("ASIN", lambda r: cell_link(r.get("asin_link"), r.get("asin") or "")),
        (t("st_sent"), lambda r: str(int(r.get("sent", 0)))),
        (t("st_already"), lambda r: str(int(r.get("already", 0)))),
        (t("st_outside"), lambda r: str(int(r.get("outside", 0)))),
    ]
    render_html_table(by_asin.to_dict("records"), columns_a, height=420)
    download_csv_button(
        by_asin[["asin", "sent", "already", "outside"]],
        "review_by_asin", key="reviews_asin_csv")

st.caption(t("reviews_cache_note"))
