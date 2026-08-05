# -*- coding: utf-8 -*-
"""Merinoprotect Dashboard — Огляд / Overview."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import (ACCENT, ACCENT2, AMAZON_DOMAINS, inject_css, lang_selector,
                metric_card, mp_label, plotly_layout, q, t)

st.set_page_config(layout="wide", page_title="Merinoprotect", page_icon="🐑")
lang_selector()
inject_css()

st.markdown(f"## {t('overview_title')}")

# ------------------------------------------------------------ фільтри ----
mps = q("SELECT DISTINCT marketplace_id FROM merinoprotect.orders ORDER BY 1")
mp_options = ["All"] + mps["marketplace_id"].dropna().tolist()

fc1, fc2, _ = st.columns([2, 2, 6])
with fc1:
    mp_sel = st.selectbox(t("marketplace"), mp_options, format_func=mp_label, key="mp")
with fc2:
    period = st.selectbox(t("period"), [7, 14, 30], index=1,
                          format_func=lambda d: f"{d} {t('days')}", key="period")

now_utc = datetime.now(timezone.utc)
date_from = (now_utc - timedelta(days=period)).strftime("%Y-%m-%d")
prev_from = (now_utc - timedelta(days=period * 2)).strftime("%Y-%m-%d")

mp_where = "" if mp_sel == "All" else "AND marketplace_id = %s"
mp_params: tuple = () if mp_sel == "All" else (mp_sel,)

# ------------------------------------------------------------- дані ----
# одразу 2 періоди (поточний + попередній) для дельт
orders_2p = q(f"""
    SELECT amazon_order_id, purchase_date, order_status, marketplace_id,
           order_total_amount, order_total_currency
    FROM merinoprotect.orders
    WHERE purchase_date >= %s::date
      AND order_status <> 'Canceled'
      {mp_where}
""", (prev_from, *mp_params))

if orders_2p.empty:
    st.info(t("no_orders"))
    st.stop()

orders_2p["purchase_date"] = pd.to_datetime(orders_2p["purchase_date"], utc=True)
orders_2p["day"] = orders_2p["purchase_date"].dt.date
orders_2p["order_total_amount"] = pd.to_numeric(
    orders_2p["order_total_amount"], errors="coerce").fillna(0)

cutoff = (now_utc - timedelta(days=period)).date()
orders = orders_2p[orders_2p["day"] >= cutoff].copy()
orders_prev = orders_2p[orders_2p["day"] < cutoff]

if orders.empty:
    st.info(t("no_orders"))
    st.stop()

n_orders = len(orders)
n_prev = len(orders_prev)

rev_by_cur = (orders.groupby("order_total_currency")["order_total_amount"]
              .sum().sort_values(ascending=False))
rev_by_cur = rev_by_cur[rev_by_cur.index.notna()]
if len(rev_by_cur):
    main_cur = rev_by_cur.index[0]
    main_rev = rev_by_cur.iloc[0]
    other = " · ".join(f"{v:,.0f} {c}" for c, v in rev_by_cur.iloc[1:].items())
else:
    main_cur, main_rev, other = "", 0.0, ""

prev_rev = orders_prev.loc[
    orders_prev["order_total_currency"] == main_cur, "order_total_amount"].sum()

main_cur_orders = orders[orders["order_total_currency"] == main_cur]
avg_check = (main_cur_orders["order_total_amount"].mean()
             if len(main_cur_orders) else 0)

orders_today = int((orders["day"] == now_utc.date()).sum())
pending_count = int((orders["order_status"] == "Pending").sum())


def pct_delta(cur, prev):
    if not prev:
        return None, True
    change = (cur - prev) / prev * 100
    return f"{abs(change):.0f}%", change >= 0


# ------------------------------------------------------------ картки ----
d_orders, up_orders = pct_delta(n_orders, n_prev)
d_rev, up_rev = pct_delta(main_rev, prev_rev)

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(f"{t('orders_n')} · {period} {t('days')}", f"{n_orders:,}",
                delta=d_orders, delta_up=up_orders)
with c2:
    metric_card(f"{t('revenue')} · {period} {t('days')}",
                f"{main_rev:,.0f} {main_cur}",
                delta=d_rev, delta_up=up_rev,
                sub=other if other else None)
with c3:
    metric_card(t("avg_check"), f"{avg_check:,.2f} {main_cur}")
with c4:
    metric_card(t("orders_today"), f"{orders_today}",
                sub=f"Pending: {pending_count}")

st.markdown("")

# ------------------------------------------------------ графік: дні ----
daily = (orders.groupby("day")
         .agg(orders=("amazon_order_id", "count")).reset_index())
daily_rev = (main_cur_orders.groupby("day")["order_total_amount"]
             .sum().reset_index(name="revenue"))
daily = daily.merge(daily_rev, on="day", how="left").fillna(0)

fig = go.Figure()
fig.add_bar(x=daily["day"], y=daily["orders"], name=t("orders_series"),
            marker_color=ACCENT, opacity=0.85)
fig.add_scatter(x=daily["day"], y=daily["revenue"],
                name=f"{t('revenue_series')}, {main_cur}",
                yaxis="y2", mode="lines+markers",
                line=dict(color=ACCENT2, width=2))
fig.update_layout(
    **plotly_layout(),
    title=t("chart_daily"),
    yaxis2=dict(overlaying="y", side="right", showgrid=False),
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------- топ SKU + останні замовлення ----
g1, g2 = st.columns([1, 1])

with g1:
    top_sku = q(f"""
        SELECT oi.seller_sku, SUM(oi.quantity_ordered) AS qty
        FROM merinoprotect.order_items oi
        JOIN merinoprotect.orders o USING (amazon_order_id)
        WHERE o.purchase_date >= %s::date
          AND o.order_status <> 'Canceled'
          {mp_where.replace('marketplace_id', 'o.marketplace_id')}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """, (date_from, *mp_params))

    if not top_sku.empty:
        top_sku = top_sku.sort_values("qty")
        f2 = go.Figure(go.Bar(
            x=top_sku["qty"], y=top_sku["seller_sku"], orientation="h",
            marker_color=ACCENT, text=top_sku["qty"], textposition="outside",
        ))
        f2.update_layout(**plotly_layout(), title=t("top10_sku"))
        st.plotly_chart(f2, use_container_width=True)

with g2:
    st.markdown(f"**{t('last20')}**")

    last20 = orders.sort_values("purchase_date", ascending=False).head(20).copy()

    # перший товар кожного замовлення: ASIN + фото
    order_ids = tuple(last20["amazon_order_id"].tolist())
    if order_ids:
        items_info = q("""
            SELECT DISTINCT ON (oi.amazon_order_id)
                   oi.amazon_order_id, oi.asin, c.image_url
            FROM merinoprotect.order_items oi
            LEFT JOIN merinoprotect.orders o USING (amazon_order_id)
            LEFT JOIN merinoprotect.catalog_images c
              ON c.asin = oi.asin AND c.marketplace_id = o.marketplace_id
            WHERE oi.amazon_order_id IN %s
            ORDER BY oi.amazon_order_id, oi.order_item_id
        """, (order_ids,))
        last20 = last20.merge(items_info, on="amazon_order_id", how="left")
    else:
        last20["asin"] = None
        last20["image_url"] = None

    last20["asin_link"] = (
        "https://" + last20["marketplace_id"].map(AMAZON_DOMAINS).fillna("amazon.com")
        + "/dp/" + last20["asin"].fillna("")
    )

    last20[t("col_market")] = last20["marketplace_id"].map(mp_label)
    last20[t("col_date")] = last20["purchase_date"].dt.strftime("%d.%m %H:%M")
    last20[t("col_sum")] = last20.apply(
        lambda r: "—" if pd.isna(r["order_total_amount"]) or r["order_total_amount"] == 0
        else f"{r['order_total_amount']:,.2f} {r['order_total_currency'] or ''}",
        axis=1,
    )

    show20 = (last20[["image_url", "amazon_order_id", "asin_link",
                      t("col_date"), "order_status", t("col_market"), t("col_sum")]]
              .rename(columns={
                  "image_url": t("col_photo"),
                  "amazon_order_id": t("col_order"),
                  "asin_link": "ASIN",
                  "order_status": t("col_status"),
              }))

    st.dataframe(
        show20,
        hide_index=True, use_container_width=True, height=420,
        column_config={
            t("col_photo"): st.column_config.ImageColumn("", width="small"),
            "ASIN": st.column_config.LinkColumn("ASIN", display_text=r".*/dp/(.*)"),
        },
    )

st.caption(t("cache_note"))
