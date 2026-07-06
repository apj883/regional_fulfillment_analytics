"""
Interactive HTML dashboard for the Regional Outbound Fulfillment case study.
Builds Plotly figures from the KPI tables and assembles a single self-
contained dashboard.html (no external dependencies besides the Plotly CDN).
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

DATA = "/sessions/serene-amazing-cori/work/data"
OUT_HTML = "/sessions/serene-amazing-cori/work/dashboard/dashboard.html"

NAVY = "#2B2620"    # charcoal-ink (renamed usage: primary dark, no blue)
TEAL = "#4B6B43"    # forest/olive green (secondary)
CORAL = "#C1592E"   # terracotta
GOLD = "#C68E17"    # amber/gold
GREY = "#8C8C8C"
RED = "#7A2E38"     # deep wine/burgundy

TEMPLATE = "plotly_white"

def style(fig, title, height=380):
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, family="Arial", color="#1a1a1a"), x=0.02),
        template=TEMPLATE,
        height=height,
        margin=dict(l=50, r=30, t=55, b=45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Arial", size=12),
    )
    return fig

figs = {}

# 1. OTIF by carrier
otif_c = pd.read_csv(f"{DATA}/kpi_otif_by_carrier.csv")
fig = go.Figure(go.Bar(x=otif_c["Shipping Mode"], y=otif_c["otif_rate"]*100,
                        marker_color=NAVY, text=[f"{v:.1f}%" for v in otif_c["otif_rate"]*100],
                        textposition="outside"))
fig.update_yaxes(title="OTIF rate (%)")
figs["otif_carrier"] = style(fig, "OTIF Rate by Carrier / Service Level")

# 2. OTIF monthly trend
otif_m = pd.read_csv(f"{DATA}/kpi_otif_monthly.csv")
fig = go.Figure()
fig.add_trace(go.Scatter(x=otif_m["order_month"], y=otif_m["otif_rate"]*100, name="OTIF rate",
                          line=dict(color=NAVY, width=2.5), fill="tozeroy", fillcolor="rgba(31,58,95,0.08)"))
fig.add_trace(go.Scatter(x=otif_m["order_month"], y=otif_m["on_time_rate"]*100, name="On-time rate",
                          line=dict(color=TEAL, width=2, dash="dash")))
fig.update_yaxes(title="Rate (%)")
figs["otif_trend"] = style(fig, "Monthly OTIF & On-Time Trend")

# 3. Cost per order by region
cpo_rc = pd.read_csv(f"{DATA}/kpi_cpo_region_carrier.csv")
cpo_region = cpo_rc.groupby("Order Region", as_index=False)["total_cost"].sum().sort_values("total_cost", ascending=False).head(12)
fig = go.Figure(go.Bar(x=cpo_region["total_cost"], y=cpo_region["Order Region"], orientation="h",
                        marker_color=TEAL, text=[f"${v:,.0f}" for v in cpo_region["total_cost"]], textposition="outside"))
fig.update_layout(yaxis=dict(autorange="reversed"))
fig.update_xaxes(title="Total outbound shipping cost ($)")
figs["cost_region"] = style(fig, "Total Outbound Shipping Cost by Region (Top 12)", height=430)

# 4. Margin leakage by region
leak = cpo_rc.groupby("Order Region", as_index=False)["total_margin_leakage"].sum().sort_values("total_margin_leakage", ascending=False).head(10)
fig = go.Figure(go.Bar(x=leak["Order Region"], y=leak["total_margin_leakage"], marker_color=CORAL))
fig.update_yaxes(title="Margin leakage ($)")
figs["leakage"] = style(fig, "Shipping Margin Leakage by Region (Top 10)")

# 5. EDD accuracy
edd = pd.read_csv(f"{DATA}/kpi_edd_by_carrier.csv")
fig = go.Figure()
fig.add_trace(go.Bar(x=edd["Shipping Mode"], y=edd["edd_met_rate"]*100, name="EDD met rate", marker_color=NAVY, yaxis="y1"))
fig.add_trace(go.Scatter(x=edd["Shipping Mode"], y=edd["avg_variance"], name="Avg transit variance (days)",
                          line=dict(color=CORAL, width=2.5), marker=dict(size=9), yaxis="y2"))
fig.update_layout(
    yaxis=dict(title="EDD met rate (%)"),
    yaxis2=dict(title="Transit variance (days)", overlaying="y", side="right"),
)
figs["edd"] = style(fig, "EDD Accuracy by Carrier")

# 6. Failed delivery pareto
pf = pd.read_csv(f"{DATA}/kpi_failed_delivery_region.csv").head(10)
fig = go.Figure()
fig.add_trace(go.Bar(x=pf["Order Region"], y=pf["failed_orders"], name="Failed orders", marker_color=RED, yaxis="y1"))
fig.add_trace(go.Scatter(x=pf["Order Region"], y=pf["cum_pct"]*100, name="Cumulative %",
                          line=dict(color=NAVY, width=2.5), marker=dict(size=8), yaxis="y2"))
fig.update_layout(
    yaxis=dict(title="Failed / cancelled orders"),
    yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 100]),
)
figs["pareto"] = style(fig, "Failed Delivery Root-Cause Pareto (by Region)")

# 7. Cross border
cb = pd.read_csv(f"{DATA}/kpi_cross_border_summary.csv")
metrics = ["otif_rate", "on_time_rate_post_customs_adj", "cancel_rate"]
labels = ["OTIF rate", "On-time (w/ customs buffer)", "Cancellation rate"]
fig = go.Figure()
for i, lane in enumerate(cb["lane"]):
    vals = [cb.loc[cb["lane"] == lane, m].values[0]*100 for m in metrics]
    fig.add_trace(go.Bar(x=labels, y=vals, name=lane, marker_color=[NAVY, CORAL][i]))
fig.update_layout(barmode="group")
fig.update_yaxes(title="Rate (%)")
figs["cross_border"] = style(fig, "Cross-Border: Domestic US vs. US to Canada")

# 8. Corporate seasonal surge
cm = pd.read_csv(f"{DATA}/kpi_corporate_monthly.csv")
mean_v = cm["orders"].mean()
std_v = cm["orders"].std()
thresh = mean_v + std_v
fig = go.Figure()
fig.add_trace(go.Scatter(x=cm["order_month"], y=cm["orders"], name="Corporate orders/month",
                          line=dict(color=NAVY, width=2.5), fill="tozeroy", fillcolor="rgba(31,58,95,0.10)"))
fig.add_hline(y=thresh, line_dash="dash", line_color=CORAL, annotation_text="Surge threshold (+1 std dev)")
surge = cm[cm["orders"] > thresh]
fig.add_trace(go.Scatter(x=surge["order_month"], y=surge["orders"], mode="markers", name="Surge month",
                          marker=dict(color=CORAL, size=10)))
fig.update_yaxes(title="Corporate (B2B) orders / month")
figs["surge"] = style(fig, "Corporate Segment Seasonal Surge Detection")

# 9. Savings by lever
lv = pd.read_csv(f"{DATA}/kpi_savings_by_lever.csv")
fig = go.Figure(go.Bar(x=lv["lever"], y=lv["annual_savings"], marker_color=[NAVY, TEAL, GOLD],
                        text=[f"${v:,.0f}<br>({p:.1%})" for v, p in zip(lv["annual_savings"], lv["pct_of_total_cost"])],
                        textposition="outside"))
fig.update_yaxes(title="Simulated annual savings ($)")
figs["savings"] = style(fig, "Cost-per-Order Reduction Opportunity by Lever")

# 10. Corporate category mix
cc = pd.read_csv(f"{DATA}/kpi_corporate_category.csv").head(8)
fig = go.Figure(go.Bar(x=cc["total_units"], y=cc["Category Name"], orientation="h", marker_color=TEAL))
fig.update_layout(yaxis=dict(autorange="reversed"))
fig.update_xaxes(title="Total units ordered")
figs["corp_mix"] = style(fig, "Corporate Segment — Top Categories by Volume", height=430)

# ---- Top-line KPI summary cards ----
summary = pd.read_csv(f"{DATA}/kpi_topline_summary.csv", index_col=0).iloc[:, 0]

def fmt_money(v):
    return f"${float(v):,.0f}"

def fmt_pct(v):
    return f"{float(v)*100:.1f}%"

cards = [
    ("Total Orders Analyzed", f"{int(float(summary['total_orders'])):,}"),
    ("OTIF Rate", fmt_pct(summary["otif_rate"])),
    ("Avg. Cost per Order", fmt_money(summary["avg_cost_per_order"])),
    ("Total Outbound Shipping Cost", fmt_money(summary["total_shipping_cost"])),
    ("Margin Leakage Identified", fmt_money(summary["total_margin_leakage"])),
    ("Reshipment Cost (Failed Deliveries)", fmt_money(summary["total_reshipment_cost"])),
    ("Simulated Annual Savings", fmt_money(summary["simulated_annual_savings"]) + f" ({fmt_pct(summary['simulated_savings_pct'])})"),
    ("Cross-Border (USCA) Orders", f"{int(float(summary['usca_cross_border_orders'])):,}"),
]

card_html = "".join(
    f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>'
    for label, value in cards
)

chart_divs = {k: pio.to_html(fig, include_plotlyjs=False, full_html=False, config={"displaylogo": False})
              for k, fig in figs.items()}

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Regional Outbound Fulfillment & Logistics Analytics Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, Helvetica, sans-serif; background: #F5F1EA; margin: 0; padding: 0; color: #1a1a1a; }}
  header {{ background: linear-gradient(135deg, #2B2620 0%, #4B6B43 100%); color: white; padding: 28px 36px; }}
  header h1 {{ margin: 0 0 6px 0; font-size: 26px; }}
  header p {{ margin: 0; opacity: 0.9; font-size: 14px; max-width: 900px; line-height: 1.5; }}
  .kpi-row {{ display: flex; flex-wrap: wrap; gap: 14px; padding: 22px 36px; }}
  .kpi-card {{ background: white; border-radius: 10px; padding: 14px 18px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
               flex: 1 1 190px; min-width: 190px; border-left: 4px solid #4B6B43; }}
  .kpi-label {{ font-size: 11.5px; color: #666; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 6px; }}
  .kpi-value {{ font-size: 21px; font-weight: 700; color: #2B2620; }}
  .section-title {{ padding: 24px 36px 4px 36px; font-size: 18px; font-weight: 700; color: #2B2620; border-top: 1px solid #ddd; margin-top: 6px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding: 12px 36px 36px 36px; }}
  .grid .full {{ grid-column: 1 / span 2; }}
  .chart-card {{ background: white; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); padding: 8px; }}
  footer {{ padding: 18px 36px 40px 36px; font-size: 11.5px; color: #777; line-height: 1.6; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} .grid .full {{ grid-column: 1; }} }}
</style>
</head>
<body>
<header>
  <h1>Regional Outbound Fulfillment &amp; Logistics Analytics</h1>
  <p>Data source: DataCo Smart Supply Chain Dataset (Kaggle) — 178,626 orders, Jan 2015-Jan 2018, global
  sporting-goods/apparel retailer. Outbound shipping cost, margin leakage, and savings figures are a
  transparent cost model layered on real order-level operational fields (see methodology in the full report).</p>
</header>

<div class="kpi-row">{card_html}</div>

<div class="section-title">3PL SLA Performance — OTIF, On-Time Rate &amp; Trend</div>
<div class="grid">
  <div class="chart-card">{chart_divs['otif_carrier']}</div>
  <div class="chart-card">{chart_divs['otif_trend']}</div>
</div>

<div class="section-title">Cost per Order &amp; Margin Leakage</div>
<div class="grid">
  <div class="chart-card full">{chart_divs['cost_region']}</div>
  <div class="chart-card full">{chart_divs['leakage']}</div>
</div>

<div class="section-title">EDD Accuracy &amp; Failed Delivery Root Cause</div>
<div class="grid">
  <div class="chart-card">{chart_divs['edd']}</div>
  <div class="chart-card">{chart_divs['pareto']}</div>
</div>

<div class="section-title">Cross-Border US &lt;-&gt; Canada</div>
<div class="grid">
  <div class="chart-card full">{chart_divs['cross_border']}</div>
</div>

<div class="section-title">Corporate (B2B) Segment — Seasonal Surge &amp; Category Mix</div>
<div class="grid">
  <div class="chart-card">{chart_divs['surge']}</div>
  <div class="chart-card">{chart_divs['corp_mix']}</div>
</div>

<div class="section-title">Cost Reduction Opportunity</div>
<div class="grid">
  <div class="chart-card full">{chart_divs['savings']}</div>
</div>

<footer>
  Methodology: OTIF = delivered on/before the scheduled transit window AND not cancelled. Cost per Order is a
  documented parcel-pricing model (base rate by service level x regional zone factor + quantity surcharge),
  not a vendor invoice figure — the public dataset does not expose carrier billing data. Savings simulation
  assumes three independent levers (carrier diversification, zone skipping, packaging optimization) applied to
  eligible order volume at stated adoption rates. Cross-border on-time figures include a modeled +1 day CBSA
  customs-clearance buffer for Canada-bound orders. Built with Python (pandas, Plotly) on the DataCo Smart
  Supply Chain dataset (Kaggle / kagglehub: shashwatwork/dataco-smart-supply-chain-for-big-data-analysis).
</footer>
</body>
</html>
"""

with open(OUT_HTML, "w") as f:
    f.write(html)
print("Dashboard written to", OUT_HTML, "size:", len(html), "chars")
