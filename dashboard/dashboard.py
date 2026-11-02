from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="E-Commerce Dashboard", page_icon="🛒", layout="wide")
sns.set_theme(style="whitegrid")
BLUE, GREY, RED = "#2a6f97", "#c4c9cf", "#c0392b"
DATA_PATH = Path(__file__).parent / "main_data.csv"


@st.cache_data
def load_data():
    df = pd.read_csv(
        DATA_PATH,
        parse_dates=["order_purchase_timestamp", "order_delivered_customer_date",
                     "order_estimated_delivery_date"],
    )
    df["month"] = df.order_purchase_timestamp.dt.to_period("M").dt.to_timestamp()
    return df


def money(v, pos=None):
    return f"R$ {v/1e6:.1f} jt" if abs(v) >= 1e6 else f"R$ {v/1e3:.0f} rb"


def order_level(df):
    """Satu baris per pesanan (untuk analisis review & keterlambatan)."""
    return (df.drop_duplicates("order_id")
            [["order_id", "customer_unique_id", "customer_state", "review_score", "delay_days",
              "geolocation_lat", "geolocation_lng", "month"]]
            .assign(is_late=lambda d: d.delay_days > 0))


def rfm_table(df):
    d = df.copy()
    ref = d.order_purchase_timestamp.max() + pd.Timedelta(days=1)
    rfm = d.groupby("customer_unique_id").agg(
        last=("order_purchase_timestamp", "max"), frequency=("order_id", "nunique"),
        monetary=("price", "sum"))
    rfm["recency"] = (ref - rfm["last"]).dt.days
    if len(rfm) < 10:
        return rfm.assign(segment="Data terlalu sedikit")
    rfm["R"] = pd.qcut(rfm.recency.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["M"] = pd.qcut(rfm.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    def seg(r):
        if r.frequency >= 2: return "Repeat Customers"
        if r.R >= 4 and r.M >= 4: return "Recent High-Spenders"
        if r.R >= 4: return "Recent Customers"
        if r.R <= 2 and r.M >= 4: return "At-Risk High-Spenders"
        if r.R <= 2: return "Dormant"
        return "Need Attention"

    rfm["segment"] = rfm.apply(seg, axis=1)
    return rfm


df_all = load_data()

# ---------------- Sidebar ----------------
st.sidebar.title("🛒 Filter")
min_d, max_d = df_all.order_purchase_timestamp.min().date(), df_all.order_purchase_timestamp.max().date()
date_range = st.sidebar.date_input("Rentang tanggal order", (min_d, max_d), min_value=min_d, max_value=max_d)
states = sorted(df_all.customer_state.unique())
sel_states = st.sidebar.multiselect("State pelanggan", states, default=states)
st.sidebar.caption("Data: Olist E-Commerce Public Dataset, pesanan *delivered*, Jan 2017 – Agu 2018.")

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)
else:
    start, end = pd.to_datetime(min_d), pd.to_datetime(max_d) + pd.Timedelta(days=1)

df = df_all[(df_all.order_purchase_timestamp >= start) & (df_all.order_purchase_timestamp < end)
            & (df_all.customer_state.isin(sel_states))]

st.title("Dashboard Analisis E-Commerce (Olist)")
if df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

orders = order_level(df)

# ---------------- KPI ----------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total pesanan", f"{orders.order_id.nunique():,}")
c2.metric("Pelanggan unik", f"{orders.customer_unique_id.nunique():,}")
c3.metric("Total revenue", f"R$ {df.price.sum()/1e6:.2f} jt")
c4.metric("Rata-rata review", f"{orders.review_score.mean():.2f}")
c5.metric("Pesanan terlambat", f"{orders.is_late.mean()*100:.1f}%")

tab1, tab2, tab3, tab4 = st.tabs(["📦 Kategori Produk", "🚚 Keterlambatan & Review", "👥 RFM", "🗺️ Geospasial"])

# ---------------- Tab 1 ----------------
with tab1:
    st.subheader("Pertanyaan 1: Kategori produk apa saja yang termasuk penyumbang revenue tertinggi dan terendah, dan berapa persen kontribusi kategori teratas?")
    cat = (df[df.product_category != "unknown"].groupby("product_category")
           .agg(revenue=("price", "sum"), items=("order_id", "count")).sort_values("revenue", ascending=False))
    n = st.slider("Jumlah kategori ditampilkan", 5, 15, 10)
    total = df.price.sum()
    st.caption(f"{n} kategori teratas menyumbang **{cat.head(n).revenue.sum()/total*100:.1f}%** dari total revenue pada filter ini.")

    col_a, col_b = st.columns(2)
    with col_a:
        top = cat.head(n).sort_values("revenue")
        fig, ax = plt.subplots(figsize=(7, 0.45 * n + 1.5))
        ax.barh(top.index, top.revenue, color=BLUE)
        for y, v in enumerate(top.revenue):
            ax.text(v, y, f"  {money(v)}", va="center", fontsize=8)
        ax.set_xlim(0, top.revenue.max() * 1.25)
        ax.xaxis.set_major_formatter(mtick.FuncFormatter(money)); ax.xaxis.set_major_locator(mtick.MaxNLocator(4))
        ax.set_title(f"{n} kategori revenue TERTINGGI", loc="left", fontweight="bold"); ax.grid(axis="y", visible=False)
        st.pyplot(fig)
    with col_b:
        bot = cat.tail(n).sort_values("revenue", ascending=False)
        fig, ax = plt.subplots(figsize=(7, 0.45 * n + 1.5))
        ax.barh(bot.index, bot.revenue, color=GREY)
        for y, v in enumerate(bot.revenue):
            ax.text(v, y, f"  R$ {v:,.0f}", va="center", fontsize=8)
        ax.set_xlim(0, bot.revenue.max() * 1.3)
        ax.xaxis.set_major_locator(mtick.MaxNLocator(4))
        ax.set_title(f"{n} kategori revenue TERENDAH", loc="left", fontweight="bold"); ax.grid(axis="y", visible=False)
        st.pyplot(fig)

    st.markdown("**Revenue bulanan 5 kategori teratas**")
    top5 = list(cat.head(5).index)
    trend = (df[df.product_category.isin(top5)]
             .pivot_table(index="month", columns="product_category", values="price", aggfunc="sum")
             .reindex(columns=top5))
    fig, ax = plt.subplots(figsize=(12, 4.5))
    for col, color in zip(trend.columns, sns.color_palette("deep", 5)):
        ax.plot(trend.index, trend[col], marker="o", ms=4, lw=2, label=col, color=color)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(money)); ax.set_xlabel(""); ax.set_ylabel("Revenue (price)")
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.1), frameon=False)
    ax.set_title("Revenue bulanan 5 kategori teratas", loc="left", fontweight="bold")
    st.pyplot(fig)

# ---------------- Tab 2 ----------------
with tab2:
    st.subheader("Pertanyaan 2: Seberapa besar selisih review score pesanan terlambat vs tepat waktu, dan di state mana keterlambatan paling tinggi?")
    o = orders.dropna(subset=["delay_days"]).copy()
    o["group"] = pd.cut(o.delay_days, [-np.inf, -7, 0, 3, 7, np.inf],
                        labels=["Lebih awal >7 hari", "Lebih awal 0-7 hari", "Telat 0-3 hari", "Telat 3-7 hari", "Telat >7 hari"])
    on_t, late = o[~o.is_late].review_score.mean(), o[o.is_late].review_score.mean()
    if pd.notna(on_t) and pd.notna(late):
        st.caption(f"Review tepat waktu **{on_t:.2f}** vs terlambat **{late:.2f}** (selisih {on_t-late:.2f} poin).")

    col_a, col_b = st.columns(2)
    with col_a:
        g = o.groupby("group", observed=True).agg(avg=("review_score", "mean"), n=("order_id", "count"))
        fig, ax = plt.subplots(figsize=(7, 4.5))
        colors = [BLUE, BLUE, "#e59866", RED, RED][: len(g)] if len(g) == 5 else BLUE
        bars = ax.bar(g.index.astype(str), g.avg, color=colors)
        for b, nn in zip(bars, g.n):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05, f"{b.get_height():.2f}\n(n={nn:,})", ha="center", fontsize=8)
        ax.set_ylim(0, 5.3); ax.set_ylabel("Rata-rata review (1-5)"); ax.tick_params(axis="x", rotation=25)
        ax.set_title("Review score per kelompok ketepatan waktu", loc="left", fontweight="bold"); ax.grid(axis="x", visible=False)
        st.pyplot(fig)
    with col_b:
        min_orders = st.number_input("Minimal pesanan per state", 1, 500, 100, step=10)
        s = (o.groupby("customer_state").agg(orders=("order_id", "count"), late=("is_late", "mean")).query("orders >= @min_orders"))
        s["late"] *= 100
        s = s.sort_values("late", ascending=False).head(10).sort_values("late")
        fig, ax = plt.subplots(figsize=(7, 4.5))
        if len(s):
            avg_late = o.is_late.mean() * 100
            ax.barh(s.index, s.late, color=[RED if v > avg_late * 1.5 else "#e59866" for v in s.late])
            ax.axvline(avg_late, color="black", ls="--", lw=1, label=f"Rata-rata: {avg_late:.1f}%")
            for y, (p, nn) in enumerate(zip(s.late, s.orders)):
                ax.text(p, y, f"  {p:.1f}% (n={nn:,})", va="center", fontsize=8)
            ax.set_xlim(0, s.late.max() * 1.35); ax.legend(loc="lower right", frameon=False)
        ax.set_xlabel("% pesanan terlambat"); ax.grid(axis="y", visible=False)
        ax.set_title("10 state dengan keterlambatan tertinggi", loc="left", fontweight="bold")
        st.pyplot(fig)

# ---------------- Tab 3 ----------------
with tab3:
    st.subheader("Segmentasi pelanggan (RFM)")
    st.caption("Recency = hari sejak pembelian terakhir, Frequency = jumlah pesanan, Monetary = total belanja. "
               "Segmen dibuat dengan aturan bisnis (tanpa machine learning).")
    rfm = rfm_table(df)
    seg = (rfm.groupby("segment").agg(customers=("monetary", "size"), revenue=("monetary", "sum"),
                                      avg_recency=("recency", "mean"), avg_monetary=("monetary", "mean")))
    seg["% pelanggan"] = seg.customers / seg.customers.sum() * 100
    seg["% revenue"] = seg.revenue / seg.revenue.sum() * 100
    seg = seg.sort_values("% revenue", ascending=False)

    m1, m2, m3 = st.columns(3)
    m1.metric("Rata-rata recency (hari)", f"{rfm.recency.mean():.0f}")
    m2.metric("Rata-rata frequency", f"{rfm.frequency.mean():.2f}")
    m3.metric("Rata-rata monetary", f"R$ {rfm.monetary.mean():,.0f}")

    fig, ax = plt.subplots(figsize=(12, 4.5))
    x = np.arange(len(seg)); w = 0.38
    ax.bar(x - w / 2, seg["% pelanggan"], w, label="% pelanggan", color=GREY)
    ax.bar(x + w / 2, seg["% revenue"], w, label="% revenue", color=BLUE)
    for i, (c, r) in enumerate(zip(seg["% pelanggan"], seg["% revenue"])):
        ax.text(i - w / 2, c + 0.4, f"{c:.1f}%", ha="center", fontsize=8)
        ax.text(i + w / 2, r + 0.4, f"{r:.1f}%", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(seg.index, rotation=12); ax.legend(frameon=False); ax.grid(axis="x", visible=False)
    ax.set_title("Porsi pelanggan vs porsi revenue per segmen", loc="left", fontweight="bold")
    st.pyplot(fig)
    st.dataframe(seg.round(1))

# ---------------- Tab 4 ----------------
with tab4:
    st.subheader("Sebaran pesanan & keterlambatan per state")
    gs = (orders.dropna(subset=["geolocation_lat"]).groupby("customer_state")
          .agg(lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean"),
               orders=("order_id", "count"), late=("is_late", "mean")))
    gs["late"] *= 100
    if len(gs):
        fig, ax = plt.subplots(figsize=(8, 7))
        sc = ax.scatter(gs.lng, gs.lat, s=gs.orders / max(gs.orders.max() / 2500, 1) + 60, c=gs.late,
                        cmap="YlOrRd", edgecolor="black", linewidth=0.6, alpha=0.85)
        for st_, r in gs.iterrows():
            ax.annotate(st_, (r.lng, r.lat), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8, fontweight="bold")
        plt.colorbar(sc, ax=ax, shrink=0.7).set_label("% pesanan terlambat")
        ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude"); ax.grid(alpha=0.3)
        ax.set_title("Ukuran gelembung = jumlah pesanan", loc="left", fontweight="bold")
        st.pyplot(fig)
    st.caption("Titik state = rata-rata koordinat kode pos pelanggan pada state tersebut.")
