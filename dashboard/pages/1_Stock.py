# -*- coding: utf-8 -*-
"""Merinoprotect Dashboard — Залишки FBA / Stock."""

import os
import sys

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (ACCENT, PLOTLY_LAYOUT, inject_css, lang_selector,
                metric_card, mp_label, q, t)

st.set_page_config(layout="wide", page_title="Merinoprotect · Stock",
                   page_icon="🐑")
inject_css()
lang_selector()

st.markdown(f"## {t('stock_title')}")

snap = q("SELECT MAX(snapshot_date) AS d FROM merinoprotect.fba_inventory")
if snap.empty or snap["d"].isna().all():
    st.info(t("no_inventory"))
    st.stop()
snapshot_date = snap["d"].iloc[0]

inv = q("""
    SELECT marketplace_id, seller_sku, asin, product_name,
           fulfillable_quantity,
           COALESCE(inbound_working_quantity,0)
             + COALESCE(inbound_shipped_quantity,0)
             + COALESCE(inbound_receiving_quantity,0) AS inbound_total,
           reserved_total, unfulfillable_total, total_quantity
    FROM merinoprotect.fba_inventory
    WHERE snapshot_date = %s
""", (snapshot_date,))

# фильтры
fc1, fc2, _ = st.columns([2, 3, 5])
with fc1:
    mp_options = ["All"] + sorted(inv["marketplace_id"].dropna().unique().tolist())
    mp_sel = st.selectbox(t("marketplace"), mp_options, format_func=mp_label)
with fc2:
    search = st.text_input(t("search"), "")

df = inv.copy()
if mp_sel != "All":
    df = df[df["marketplace_id"] == mp_sel]
if search.strip():
    s = search.strip().lower()
    df = df[df["seller_sku"].str.lower().str.contains(s, na=False)
            | df["product_name"].str.lower().str.contains(s, na=False)]

for col in ["fulfillable_quantity", "inbound_total", "reserved_total",
            "unfulfillable_total", "total_quantity"]:
    df[col] = df[col].fillna(0).astype(int)

# карточки
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(t("sku_in_stock"),
                f"{(df['fulfillable_quantity'] > 0).sum():,}",
                sub=f"{t('total_rows')}: {len(df):,}")
with c2:
    metric_card("Fulfillable", f"{df['fulfillable_quantity'].sum():,}")
with c3:
    metric_card("Inbound", f"{df['inbound_total'].sum():,}",
                sub=t("inbound_sub"))
with c4:
    metric_card("Reserved", f"{df['reserved_total'].sum():,}")

st.markdown("")

# график
top15 = (df.groupby("seller_sku")["fulfillable_quantity"].sum()
         .sort_values(ascending=False).head(15).sort_values())
if len(top15):
    fig = go.Figure(go.Bar(
        x=top15.values, y=top15.index, orientation="h",
        marker_color=ACCENT, text=top15.values, textposition="outside",
    ))
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": 420}, title=t("top15_sku"))
    st.plotly_chart(fig, use_container_width=True)

# таблица
st.markdown(f"**{t('stock_by_sku')}** · {t('snapshot')} {snapshot_date}")

show = (df[["seller_sku", "product_name", "marketplace_id",
            "fulfillable_quantity", "inbound_total", "reserved_total",
            "unfulfillable_total", "total_quantity"]]
        .sort_values("fulfillable_quantity", ascending=False)
        .rename(columns={
            "seller_sku": "SKU", "product_name": t("col_name"),
            "marketplace_id": t("col_market"),
            "fulfillable_quantity": "Fulfillable",
            "inbound_total": "Inbound", "reserved_total": "Reserved",
            "unfulfillable_total": "Unfulf.", "total_quantity": "Total",
        }))
show[t("col_market")] = show[t("col_market")].map(mp_label)


def _row_style(row):
    if row["Fulfillable"] == 0:
        return ["background-color: rgba(239,68,68,0.12)"] * len(row)
    if row["Fulfillable"] < 20:
        return ["background-color: rgba(245,158,11,0.10)"] * len(row)
    return [""] * len(row)


st.dataframe(show.style.apply(_row_style, axis=1),
             hide_index=True, use_container_width=True, height=560)

st.caption(t("legend_stock"))
