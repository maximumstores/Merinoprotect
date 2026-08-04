# -*- coding: utf-8 -*-
"""Merinoprotect Dashboard — Обзор (заказы и выручка)."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import (ACCENT, ACCENT2, PLOTLY_LAYOUT, inject_css, metric_card,
                mp_label, q)

st.set_page_config(layout="wide", page_title="Merinoprotect", page_icon="🐑")
inject_css()

st.markdown("## 🐑 Merinoprotect — Обзор")

# ------------------------------------------------------------ фильтры ----
mps = q("SELECT DISTINCT marketplace_id FROM merinoprotect.orders ORDER BY 1")
mp_options = ["All"] + mps["marketplace_id"].dropna().tolist()

fc1, fc2, _ = st.columns([2, 2, 6])
with fc1:
    mp_sel = st.selectbox("Маркетплейс", mp_options, format_func=mp_label, key="mp")
with fc2:
    period = st.selectbox("Период", [7, 14, 30], index=1,
                          format_func=lambda d: f"{d} дней", key="period")

now_utc = datetime.now(timezone.utc)
date_from = (now_utc - timedelta(days=period)).strftime("%Y-%m-%d")
today = now_utc.strftime("%Y-%m-%d")

mp_where = "" if mp_sel == "All" else "AND marketplace_id = %s"
mp_params: tuple = () if mp_sel == "All" else (mp_sel,)

# ------------------------------------------------------------- данные ----
orders = q(f"""
    SELECT amazon_order_id,
           purchase_date,
           order_status,
           marketplace_id,
           order_total_amount,
           order_total_currency
    FROM merinoprotect.orders
    WHERE purchase_date >= %s::date
      AND order_status <> 'Canceled'
      {mp_where}
""", (date_from, *mp_params))

if orders.empty:
    st.info("Нет заказов за выбранный период.")
    st.stop()

orders["purchase_date"] = pd.to_datetime(orders["purchase_date"], utc=True)
orders["day"] = orders["purchase_date"].dt.date
orders["order_total_amount"] = pd.to_numeric(
    orders["order_total_amount"], errors="coerce").fillna(0)

n_orders = len(orders)

# выручка по валютам; основная = та, где больше всего денег
rev_by_cur = (orders.groupby("order_total_currency")["order_total_amount"]
              .sum().sort_values(ascending=False))
rev_by_cur = rev_by_cur[rev_by_cur.index.notna()]
if len(rev_by_cur):
    main_cur = rev_by_cur.index[0]
    main_rev = rev_by_cur.iloc[0]
    other = " · ".join(f"{v:,.0f} {c}" for c, v in rev_by_cur.iloc[1:].items())
else:
    main_cur, main_rev, other = "", 0.0, ""

main_cur_orders = orders[orders["order_total_currency"] == main_cur]
avg_check = (main_cur_orders["order_total_amount"].mean()
             if len(main_cur_orders) else 0)

orders_today = int((orders["day"] == now_utc.date()).sum())

# ------------------------------------------------------------ карточки ----
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(f"Заказы · {period} дн", f"{n_orders:,}")
with c2:
    metric_card(f"Выручка · {period} дн",
                f"{main_rev:,.0f} {main_cur}",
                sub=other if other else None)
with c3:
    metric_card("Средний чек", f"{avg_check:,.2f} {main_cur}")
with c4:
    metric_card("Заказов сегодня", f"{orders_today}", sub="по UTC")

st.markdown("")

# ------------------------------------------------- график: дни ----
daily = (orders.groupby("day")
         .agg(orders=("amazon_order_id", "count"))
         .reset_index())
daily_rev = (main_cur_orders.groupby("day")["order_total_amount"]
             .sum().reset_index(name="revenue"))
daily = daily.merge(daily_rev, on="day", how="left").fillna(0)

fig = go.Figure()
fig.add_bar(x=daily["day"], y=daily["orders"], name="Заказы",
            marker_color=ACCENT, opacity=0.85)
fig.add_scatter(x=daily["day"], y=daily["revenue"], name=f"Выручка, {main_cur}",
                yaxis="y2", mode="lines+markers",
                line=dict(color=ACCENT2, width=2))
fig.update_layout(
    **PLOTLY_LAYOUT,
    title="Заказы и выручка по дням",
    yaxis2=dict(overlaying="y", side="right", showgrid=False),
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------- график: топ SKU + таблица ----
g1, g2 = st.columns([1, 1])

with g1:
    top_sku = q(f"""
        SELECT oi.seller_sku,
               SUM(oi.quantity_ordered) AS qty
        FROM merinoprotect.order_items oi
        JOIN merinoprotect.orders o USING (amazon_order_id)
        WHERE o.purchase_date >= %s::date
          AND o.order_status <> 'Canceled'
          {mp_where.replace('marketplace_id', 'o.marketplace_id')}
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 10
    """, (date_from, *mp_params))

    if not top_sku.empty:
        top_sku = top_sku.sort_values("qty")
        f2 = go.Figure(go.Bar(
            x=top_sku["qty"], y=top_sku["seller_sku"],
            orientation="h", marker_color=ACCENT,
            text=top_sku["qty"], textposition="outside",
        ))
        f2.update_layout(**PLOTLY_LAYOUT, title="Топ-10 SKU по количеству")
        st.plotly_chart(f2, use_container_width=True)

with g2:
    st.markdown("**Последние 20 заказов**")
    last20 = orders.sort_values("purchase_date", ascending=False).head(20).copy()
    last20["маркет"] = last20["marketplace_id"].map(mp_label)
    last20["дата"] = last20["purchase_date"].dt.strftime("%d.%m %H:%M")
    last20["сумма"] = (last20["order_total_amount"].map("{:,.2f}".format)
                       + " " + last20["order_total_currency"].fillna(""))
    st.dataframe(
        last20[["amazon_order_id", "дата", "order_status", "маркет", "сумма"]]
        .rename(columns={"amazon_order_id": "Заказ",
                         "order_status": "Статус"}),
        hide_index=True, use_container_width=True, height=340,
    )

st.caption(f"Данные из merinoprotect.orders · обновление кэша каждые 10 мин · {today} UTC")
