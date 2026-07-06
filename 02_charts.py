"""
Chart generation for the Regional Outbound Fulfillment case study.
Reads the KPI tables produced by 01_etl_kpi_engineering.py and writes
report-ready PNGs.
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

DATA = "/sessions/serene-amazing-cori/work/data"
CHARTS = "/sessions/serene-amazing-cori/work/charts"

NAVY = "#2B2620"    # charcoal-ink (primary dark, no blue)
TEAL = "#4B6B43"    # forest/olive green (secondary)
CORAL = "#C1592E"   # terracotta
GOLD = "#C68E17"    # amber/gold
GREY = "#8C8C8C"
GREEN = "#5C7A45"   # muted olive-green
RED = "#7A2E38"     # deep wine/burgundy
PALETTE = [NAVY, TEAL, CORAL, GOLD, GREEN, GREY, RED]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "#222222",
    "text.color": "#222222",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def savefig(fig, name):
    fig.tight_layout()
    fig.savefig(f"{CHARTS}/{name}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


# 1. OTIF by carrier -----------------------------------------------------
otif_c = pd.read_csv(f"{DATA}/kpi_otif_by_carrier.csv")
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(otif_c["Shipping Mode"], otif_c["otif_rate"] * 100, color=NAVY, width=0.55)
ax.axhline(otif_c["otif_rate"].mean() * 100, color=CORAL, linestyle="--", linewidth=1.3, label="Network avg")
for b, v in zip(bars, otif_c["otif_rate"] * 100):
    ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold")
ax.set_ylabel("OTIF rate (%)")
ax.set_title("OTIF (On-Time In-Full) Rate by Service Level / Carrier Tier", fontsize=13, fontweight="bold", loc="left")
ax.set_ylim(0, max(otif_c["otif_rate"] * 100) + 12)
ax.legend(frameon=False)
savefig(fig, "01_otif_by_carrier")

# 2. OTIF monthly trend ---------------------------------------------------
otif_m = pd.read_csv(f"{DATA}/kpi_otif_monthly.csv")
otif_m["order_month"] = pd.to_datetime(otif_m["order_month"])
otif_m = otif_m.sort_values("order_month")
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(otif_m["order_month"], otif_m["otif_rate"] * 100, color=NAVY, linewidth=2, label="OTIF rate")
ax.plot(otif_m["order_month"], otif_m["on_time_rate"] * 100, color=TEAL, linewidth=1.6, linestyle="--", label="On-time rate")
ax.fill_between(otif_m["order_month"], otif_m["otif_rate"] * 100, alpha=0.08, color=NAVY)
ax.set_ylabel("Rate (%)")
ax.set_title("Monthly OTIF & On-Time Delivery Trend (2015-2018)", fontsize=13, fontweight="bold", loc="left")
ax.legend(frameon=False)
fig.autofmt_xdate()
savefig(fig, "02_otif_monthly_trend")

# 3. Cost per order by region ---------------------------------------------
cpo_rc = pd.read_csv(f"{DATA}/kpi_cpo_region_carrier.csv")
cpo_region = cpo_rc.groupby("Order Region").apply(
    lambda g: pd.Series({"orders": g["orders"].sum(), "total_cost": g["total_cost"].sum()})
).reset_index()
cpo_region["avg_cpo"] = cpo_region["total_cost"] / cpo_region["orders"]
cpo_region = cpo_region.sort_values("total_cost", ascending=False).head(12)
fig, ax = plt.subplots(figsize=(9, 6))
y = np.arange(len(cpo_region))
bars = ax.barh(y, cpo_region["total_cost"] / 1000, color=TEAL)
ax.set_yticks(y)
ax.set_yticklabels(cpo_region["Order Region"])
ax.invert_yaxis()
ax.set_xlabel("Total modeled outbound shipping cost ($ thousands)")
ax.set_title("Top 12 Regions by Total Outbound Shipping Cost", fontsize=13, fontweight="bold", loc="left")
for b, v in zip(bars, cpo_region["total_cost"] / 1000):
    ax.text(v + 4, b.get_y() + b.get_height() / 2, f"${v:,.0f}k", va="center", fontsize=9)
savefig(fig, "03_cost_per_order_by_region")

# 4. Margin leakage by region ----------------------------------------------
leak = cpo_rc.groupby("Order Region")["total_margin_leakage"].sum().sort_values(ascending=False).head(10)
fig, ax = plt.subplots(figsize=(9, 5.5))
bars = ax.bar(leak.index, leak.values / 1000, color=CORAL)
ax.set_ylabel("Margin leakage ($ thousands)")
ax.set_title("Shipping Margin Leakage by Region (Top 10)", fontsize=13, fontweight="bold", loc="left")
plt.xticks(rotation=40, ha="right")
for b, v in zip(bars, leak.values / 1000):
    ax.text(b.get_x() + b.get_width() / 2, v + 3, f"${v:,.0f}k", ha="center", fontsize=8.5)
savefig(fig, "04_margin_leakage_by_region")

# 5. EDD accuracy / transit variance by carrier ----------------------------
edd = pd.read_csv(f"{DATA}/kpi_edd_by_carrier.csv")
fig, ax1 = plt.subplots(figsize=(8, 5))
x = np.arange(len(edd))
bars = ax1.bar(x, edd["edd_met_rate"] * 100, color=NAVY, width=0.5, label="EDD met rate")
ax1.set_xticks(x)
ax1.set_xticklabels(edd["Shipping Mode"])
ax1.set_ylabel("EDD met rate (%)")
for b, v in zip(bars, edd["edd_met_rate"] * 100):
    ax1.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold")
ax2 = ax1.twinx()
ax2.plot(x, edd["avg_variance"], color=CORAL, marker="o", linewidth=2, label="Avg transit variance (days)")
ax2.set_ylabel("Avg. actual vs. scheduled transit variance (days)", color=CORAL)
ax2.tick_params(axis="y", colors=CORAL)
ax2.axhline(0, color=GREY, linewidth=0.8, linestyle=":")
ax1.set_title("EDD (Estimated Delivery Date) Accuracy by Carrier Tier", fontsize=13, fontweight="bold", loc="left")
fig.legend(loc="upper left", bbox_to_anchor=(0.12, 0.88), frameon=False)
savefig(fig, "05_edd_accuracy_by_carrier")

# 6. Failed delivery Pareto (region) ---------------------------------------
pf = pd.read_csv(f"{DATA}/kpi_failed_delivery_region.csv").head(10)
fig, ax1 = plt.subplots(figsize=(9.5, 5.5))
bars = ax1.bar(pf["Order Region"], pf["failed_orders"], color=RED, alpha=0.85)
ax1.set_ylabel("Failed / cancelled orders")
ax2 = ax1.twinx()
ax2.plot(pf["Order Region"], pf["cum_pct"] * 100, color=NAVY, marker="o", linewidth=2)
ax2.set_ylabel("Cumulative % of failed orders", color=NAVY)
ax2.tick_params(axis="y", colors=NAVY)
ax2.axhline(80, color=GOLD, linestyle="--", linewidth=1.2)
ax2.text(len(pf) - 1, 82, "80% line", color=GOLD, fontsize=9, ha="right")
ax1.set_title("Failed Delivery Root-Cause Pareto — by Region", fontsize=13, fontweight="bold", loc="left")
plt.setp(ax1.get_xticklabels(), rotation=35, ha="right")
savefig(fig, "06_failed_delivery_pareto_region")

# 7. Failed delivery by category -------------------------------------------
pc = pd.read_csv(f"{DATA}/kpi_failed_delivery_category.csv").head(10)
fig, ax = plt.subplots(figsize=(9, 5.5))
bars = ax.barh(pc["Category Name"][::-1], pc["failed_orders"][::-1], color=CORAL)
ax.set_xlabel("Failed / cancelled orders")
ax.set_title("Failed Delivery Root-Cause — by Product Category", fontsize=13, fontweight="bold", loc="left")
savefig(fig, "07_failed_delivery_by_category")

# 8. Cross-border US vs Canada ----------------------------------------------
cb = pd.read_csv(f"{DATA}/kpi_cross_border_summary.csv")
metrics = ["otif_rate", "on_time_rate_post_customs_adj", "cancel_rate"]
labels = ["OTIF rate", "On-time rate\n(incl. customs buffer)", "Cancellation rate"]
x = np.arange(len(metrics))
width = 0.35
fig, ax = plt.subplots(figsize=(9, 5.5))
for i, lane in enumerate(cb["lane"]):
    vals = [cb.loc[cb["lane"] == lane, m].values[0] * 100 for m in metrics]
    bars = ax.bar(x + (i - 0.5) * width, vals, width, label=lane, color=[NAVY, CORAL][i])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.1f}%", ha="center", fontsize=8.5)
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("Rate (%)")
ax.set_title("Cross-Border Performance: Domestic US vs. US -> Canada", fontsize=13, fontweight="bold", loc="left")
ax.legend(frameon=False, loc="upper right")
savefig(fig, "08_cross_border_us_canada")

# 9. Corporate segment monthly volume (seasonal surge) ----------------------
cm = pd.read_csv(f"{DATA}/kpi_corporate_monthly.csv")
cm["order_month"] = pd.to_datetime(cm["order_month"])
cm = cm.sort_values("order_month")
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(cm["order_month"], cm["orders"], color=NAVY, linewidth=2)
ax.fill_between(cm["order_month"], cm["orders"], alpha=0.12, color=NAVY)
mean_v = cm["orders"].mean()
std_v = cm["orders"].std()
surge_thresh = mean_v + std_v
ax.axhline(surge_thresh, color=CORAL, linestyle="--", linewidth=1.2, label=f"Surge threshold (+1 std dev)")
surge_months = cm[cm["orders"] > surge_thresh]
ax.scatter(surge_months["order_month"], surge_months["orders"], color=CORAL, zorder=5, s=45, label="Surge month")
ax.set_ylabel("Corporate (B2B) segment orders / month")
ax.set_title("Corporate Segment Order Volume — Seasonal Surge Detection", fontsize=13, fontweight="bold", loc="left")
ax.legend(frameon=False)
fig.autofmt_xdate()
savefig(fig, "09_corporate_seasonal_surge")

# 10. Savings simulation by lever --------------------------------------------
lv = pd.read_csv(f"{DATA}/kpi_savings_by_lever.csv")
fig, ax = plt.subplots(figsize=(8, 5.5))
bars = ax.bar(lv["lever"], lv["annual_savings"] / 1000, color=[NAVY, TEAL, GOLD])
ax.set_ylabel("Simulated annual savings ($ thousands)")
ax.set_title("Cost-per-Order Reduction Opportunity by Lever", fontsize=13, fontweight="bold", loc="left")
plt.xticks(rotation=12, ha="right")
for b, v, p in zip(bars, lv["annual_savings"] / 1000, lv["pct_of_total_cost"]):
    ax.text(b.get_x() + b.get_width() / 2, v + 3, f"${v:,.0f}k\n({p:.1%})", ha="center", fontsize=9.5, fontweight="bold")
savefig(fig, "10_savings_by_lever")

# 11. Corporate category mix --------------------------------------------------
cc = pd.read_csv(f"{DATA}/kpi_corporate_category.csv").head(8)
fig, ax = plt.subplots(figsize=(9, 5.5))
bars = ax.barh(cc["Category Name"][::-1], cc["total_units"][::-1], color=TEAL)
ax.set_xlabel("Total units ordered (Corporate segment)")
ax.set_title("Corporate (B2B) Segment — Top Categories by Volume", fontsize=13, fontweight="bold", loc="left")
savefig(fig, "11_corporate_category_mix")

print("All charts written to", CHARTS)
