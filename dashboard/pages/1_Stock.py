# -*- coding: utf-8 -*-
"""Merinoprotect Dashboard — Залишки FBA / Stock."""

import os
import sys

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (ACCENT, AMAZON_DOMAINS, PLOTLY_LAYOUT, inject_css,
                lang_selector, metric_card, mp_label, q, t)

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
    SELECT f.marketplace_id, f.seller_sku, f.asin, f.product_name,
           f.fulfillable_quantity,
           COALESCE(f.inbound_working_quantity,0)
             + COALESCE(f.inbound_shipped_quantity,0)
             + COALESCE(f.inbound_receiving_quantity,0) AS inbound_total,
           f.reserved_total, f.unfulfillable_total, f.total_quantity,
           c.image_url
    FROM merinoprotect.fba_inventory f
    LEFT JOIN merinoprotect.catalog_images c
      ON c.marketplace_id = f.marketplace_id AND c.asin = f.asin
    WHERE f.snapshot_date = %s
""", (snapshot_date,))

df_all = inv.copy()
for col in ["fulfillable_quantity", "inbound_total", "reserved_total",
            "unfulfillable_total", "total_quantity"]:
    df_all[col] = df_all[col].fillna(0).astype(int)

# ------------------------------------------------------------- картки ----
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(t("sku_in_stock"),
                f"{(df_all['fulfillable_quantity'] > 0).sum():,}",
                sub=f"{t('total_rows')}: {len(df_all):,}")
with c2:
    metric_card("Fulfillable", f"{df_all['fulfillable_quantity'].sum():,}")
with c3:
    metric_card("Inbound", f"{df_all['inbound_total'].sum():,}",
                sub=t("inbound_sub"))
with c4:
    metric_card("Reserved", f"{df_all['reserved_total'].sum():,}")

st.markdown("")

# --------------------------------------------------------------- графік ----
top15 = (df_all.groupby("seller_sku")["fulfillable_quantity"].sum()
         .sort_values(ascending=False).head(15).sort_values())
if len(top15):
    fig = go.Figure(go.Bar(
        x=top15.values, y=top15.index, orientation="h",
        marker_color=ACCENT, text=top15.values, textposition="outside",
    ))
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": 420}, title=t("top15_sku"))
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------- фільтри НАД таблицею ----
st.markdown(f"**{t('stock_by_sku')}** · {t('snapshot')} {snapshot_date}")

fc1, fc2, _ = st.columns([2, 3, 5])
with fc1:
    mp_options = ["All"] + sorted(df_all["marketplace_id"].dropna().unique().tolist())
    mp_sel = st.selectbox(t("marketplace"), mp_options, format_func=mp_label)
with fc2:
    search = st.text_input(t("search"), "")

df = df_all.copy()
if mp_sel != "All":
    df = df[df["marketplace_id"] == mp_sel]
if search.strip():
    s = search.strip().lower()
    df = df[df["seller_sku"].str.lower().str.contains(s, na=False)
            | df["product_name"].str.lower().str.contains(s, na=False)]

# ASIN -> клікабельне посилання на лістинг потрібного маркетплейсу
df["asin_link"] = ("https://" + df["marketplace_id"].map(AMAZON_DOMAINS).fillna("amazon.com")
                   + "/dp/" + df["asin"].fillna(""))

# --------------------------------------------------------------- таблиця ----
show = (df[["image_url", "seller_sku", "asin_link", "product_name",
            "marketplace_id", "fulfillable_quantity", "inbound_total",
            "reserved_total", "unfulfillable_total", "total_quantity"]]
        .sort_values("fulfillable_quantity", ascending=False)
        .rename(columns={
            "image_url": t("col_photo"), "seller_sku": "SKU",
            "asin_link": "ASIN", "product_name": t("col_name"),
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


st.dataframe(
    show.style.apply(_row_style, axis=1),
    hide_index=True, use_container_width=True, height=560,
    column_config={
        t("col_photo"): st.column_config.ImageColumn("", width="small"),
        "ASIN": st.column_config.LinkColumn("ASIN", display_text=r".*/dp/(.*)"),
        t("col_name"): st.column_config.TextColumn(t("col_name"), width="large"),
    },
)

st.caption(t("legend_stock"))
