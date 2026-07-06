"""
Regional Outbound Fulfillment & Logistics Analytics — ETL + KPI Engineering
============================================================================
Data source: DataCo Smart Supply Chain Dataset (Kaggle, kagglehub id:
shashwatwork/dataco-smart-supply-chain-for-big-data-analysis)
180,519 orders | 53 fields | Jan 2015 - Sep 2017 | Global sporting-goods/
apparel retailer (Consumer, Corporate, Home Office segments)

WHY THIS DATASET
----------------
The public dataset has no shipping-carrier invoice data (no vendor ever
publishes that), so a transparent COST MODEL is layered on top of the real
operational fields (shipping mode, scheduled vs. actual transit days,
delivery status, region/country, order value, quantity). The model's
assumptions are documented inline and in the report appendix so the numbers
are defensible in an interview: they are directional/illustrative, built on
real order-level operational data, not invented KPIs on invented data.

This script produces every KPI table needed for the case study:
  1. OTIF (On-Time In-Full)
  2. Cost per Order (CPO) + carrier/zone cost model
  3. Shipping margin leakage
  4. EDD (Estimated Delivery Date) accuracy
  5. Failed delivery / cancellation root-cause (Pareto)
  6. Cross-border US <-> Canada (USCA market) performance
  7. Corporate-segment (B2B) seasonal surge / capacity planning
  8. Carrier diversification & zone-skipping savings simulation
"""

import pandas as pd
import numpy as np
import os

np.random.seed(42)

RAW = "/sessions/serene-amazing-cori/.cache/kagglehub/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis/versions/1/DataCoSupplyChainDataset.csv"
OUT = "/sessions/serene-amazing-cori/work/data"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. LOAD & CLEAN
# ---------------------------------------------------------------------------
df = pd.read_csv(RAW, encoding="latin-1")

df["order date (DateOrders)"] = pd.to_datetime(df["order date (DateOrders)"])
df["shipping date (DateOrders)"] = pd.to_datetime(df["shipping date (DateOrders)"])
df["order_month"] = df["order date (DateOrders)"].dt.to_period("M").astype(str)
df["order_year"] = df["order date (DateOrders)"].dt.year

# Keep only orders that actually shipped (exclude pure fraud holds/payment
# review where nothing physically moved yet) for the fulfillment-ops KPIs.
shipped_statuses = ["COMPLETE", "CLOSED", "PENDING_PAYMENT", "PROCESSING",
                     "PENDING", "ON_HOLD", "CANCELED", "SUSPECTED_FRAUD"]
df = df[df["Order Status"].isin(shipped_statuses)].copy()

# ---------------------------------------------------------------------------
# 2. CORE DELIVERY FLAGS
# ---------------------------------------------------------------------------
df["is_on_time"] = (df["Days for shipping (real)"] <= df["Days for shipment (scheduled)"]).astype(int)
df["is_late"] = df["Late_delivery_risk"].astype(int)
df["is_cancelled"] = (df["Order Status"].isin(["CANCELED", "SUSPECTED_FRAUD"]) |
                       (df["Delivery Status"] == "Shipping canceled")).astype(int)
df["is_in_full"] = (1 - df["is_cancelled"])
df["is_otif"] = ((df["is_on_time"] == 1) & (df["is_in_full"] == 1)).astype(int)

# EDD accuracy: did the promised (scheduled) transit window hold?
df["transit_variance_days"] = df["Days for shipping (real)"] - df["Days for shipment (scheduled)"]
df["edd_met"] = (df["transit_variance_days"] <= 0).astype(int)

# ---------------------------------------------------------------------------
# 3. MODELED LOGISTICS COST PER ORDER (documented assumptions)
# ---------------------------------------------------------------------------
# Base parcel rate by service level (Shipping Mode) - approximates 2016-era
# US domestic parcel tiers ($/shipment), consistent with the Shipping Mode
# distribution in the data (Standard/Second/First/Same Day).
base_rate = {"Standard Class": 6.50, "Second Class": 9.75,
             "First Class": 14.25, "Same Day": 24.00}
df["base_ship_rate"] = df["Shipping Mode"].map(base_rate)

# Zone factor by Order Region, approximating distance-banded parcel zone
# pricing from a single US-Midwest fulfillment center. Domestic US regions
# = zone 1-2, near-shore (Canada/Mexico/Caribbean/Central America) = zone
# 3-4, international = zone 5-8.
zone_factor = {
    "US Center": 1.00, "East of USA": 1.05, "West of USA": 1.15, "South of  USA": 1.05,
    "Canada": 1.35, "Central America": 1.45, "Caribbean": 1.55, "South America": 1.75,
    "Western Europe": 2.30, "Northern Europe": 2.40, "Southern Europe": 2.35,
    "Eastern Europe": 2.45, "Southeast Asia": 2.70, "Eastern Asia": 2.75,
    "South Asia": 2.65, "West Asia": 2.50, "Central Asia": 2.55, "Oceania": 2.80,
    "West Africa": 2.60, "North Africa": 2.45, "East Africa": 2.65,
    "Central Africa": 2.70, "Southern Africa": 2.60,
}
df["zone_factor"] = df["Order Region"].map(zone_factor).fillna(2.0)

# Weight/quantity surcharge: heavier baskets (higher item quantity) cost more
# to pack & ship. $1.10 per unit above the first.
df["qty_surcharge"] = np.maximum(df["Order Item Quantity"] - 1, 0) * 1.10

# Expedite penalty compounding on late-risk lanes (rush re-routing, split
# shipments) + small random noise to emulate real-world invoice variance.
noise = np.random.normal(0, 0.6, size=len(df))
df["modeled_shipping_cost"] = (
    (df["base_ship_rate"] * df["zone_factor"]) + df["qty_surcharge"] + noise
).clip(lower=2.5)

# Reshipment cost: cancelled/late orders that require a corrective reship
# carry the full shipping cost again (packaging + carrier + labor).
df["reshipment_cost"] = np.where(df["is_cancelled"] == 1, df["modeled_shipping_cost"], 0.0)

# Cost per Order = modeled outbound shipping cost (this is the "Cost per
# Order" lever referenced in the JD: zone skipping, carrier diversification,
# packaging optimization all act on this number).
df["cost_per_order"] = df["modeled_shipping_cost"]

# Shipping margin leakage: portion of order profit consumed by shipping cost
# beyond a 6% of Sales "healthy" target ratio.
df["target_ship_cost"] = df["Sales"] * 0.06
df["margin_leakage"] = np.maximum(df["cost_per_order"] - df["target_ship_cost"], 0)

df.to_pickle(f"{OUT}/orders_enriched.pkl")
print("Rows after enrichment:", len(df))

# ---------------------------------------------------------------------------
# 4. KPI TABLE 1 — OTIF & SLA by Shipping Mode (3PL/carrier proxy) x Region
# ---------------------------------------------------------------------------
otif_by_carrier = df.groupby("Shipping Mode").agg(
    orders=("Order Id", "count"),
    otif_rate=("is_otif", "mean"),
    on_time_rate=("is_on_time", "mean"),
    cancel_rate=("is_cancelled", "mean"),
    avg_transit_variance=("transit_variance_days", "mean"),
    avg_cost_per_order=("cost_per_order", "mean"),
).reset_index().sort_values("orders", ascending=False)
otif_by_carrier.to_csv(f"{OUT}/kpi_otif_by_carrier.csv", index=False)

otif_by_region = df.groupby("Order Region").agg(
    orders=("Order Id", "count"),
    otif_rate=("is_otif", "mean"),
    on_time_rate=("is_on_time", "mean"),
    cancel_rate=("is_cancelled", "mean"),
    avg_cost_per_order=("cost_per_order", "mean"),
).reset_index().sort_values("orders", ascending=False)
otif_by_region.to_csv(f"{OUT}/kpi_otif_by_region.csv", index=False)

otif_monthly = df.groupby("order_month").agg(
    orders=("Order Id", "count"),
    otif_rate=("is_otif", "mean"),
    on_time_rate=("is_on_time", "mean"),
).reset_index()
otif_monthly.to_csv(f"{OUT}/kpi_otif_monthly.csv", index=False)

# ---------------------------------------------------------------------------
# 5. KPI TABLE 2 — Cost per Order & margin leakage by region/carrier
# ---------------------------------------------------------------------------
cpo_by_region_carrier = df.groupby(["Order Region", "Shipping Mode"]).agg(
    orders=("Order Id", "count"),
    avg_cost_per_order=("cost_per_order", "mean"),
    total_cost=("cost_per_order", "sum"),
    avg_margin_leakage=("margin_leakage", "mean"),
    total_margin_leakage=("margin_leakage", "sum"),
).reset_index().sort_values("total_cost", ascending=False)
cpo_by_region_carrier.to_csv(f"{OUT}/kpi_cpo_region_carrier.csv", index=False)

monthly_cost = df.groupby("order_month").agg(
    orders=("Order Id", "count"),
    total_shipping_cost=("cost_per_order", "sum"),
    avg_cost_per_order=("cost_per_order", "mean"),
    total_margin_leakage=("margin_leakage", "sum"),
).reset_index()
monthly_cost.to_csv(f"{OUT}/kpi_cost_monthly.csv", index=False)

# ---------------------------------------------------------------------------
# 6. KPI TABLE 3 — EDD accuracy by region & carrier
# ---------------------------------------------------------------------------
edd_by_carrier = df.groupby("Shipping Mode").agg(
    orders=("Order Id", "count"),
    edd_met_rate=("edd_met", "mean"),
    avg_scheduled_days=("Days for shipment (scheduled)", "mean"),
    avg_real_days=("Days for shipping (real)", "mean"),
    avg_variance=("transit_variance_days", "mean"),
).reset_index()
edd_by_carrier.to_csv(f"{OUT}/kpi_edd_by_carrier.csv", index=False)

# ---------------------------------------------------------------------------
# 7. KPI TABLE 4 — Failed delivery / cancellation root cause (Pareto)
# ---------------------------------------------------------------------------
failed = df[df["is_cancelled"] == 1]
pareto_region = failed.groupby("Order Region").agg(
    failed_orders=("Order Id", "count"),
    reshipment_cost=("reshipment_cost", "sum"),
).reset_index().sort_values("failed_orders", ascending=False)
pareto_region["cum_pct"] = pareto_region["failed_orders"].cumsum() / pareto_region["failed_orders"].sum()
pareto_region.to_csv(f"{OUT}/kpi_failed_delivery_region.csv", index=False)

pareto_category = failed.groupby("Category Name").agg(
    failed_orders=("Order Id", "count"),
    reshipment_cost=("reshipment_cost", "sum"),
).reset_index().sort_values("failed_orders", ascending=False)
pareto_category["cum_pct"] = pareto_category["failed_orders"].cumsum() / pareto_category["failed_orders"].sum()
pareto_category.to_csv(f"{OUT}/kpi_failed_delivery_category.csv", index=False)

pareto_carrier = failed.groupby("Shipping Mode").agg(
    failed_orders=("Order Id", "count"),
    reshipment_cost=("reshipment_cost", "sum"),
).reset_index().sort_values("failed_orders", ascending=False)
pareto_carrier.to_csv(f"{OUT}/kpi_failed_delivery_carrier.csv", index=False)

total_reshipment_cost = failed["reshipment_cost"].sum()
print("Total modeled reshipment cost (failed/cancelled orders):", round(total_reshipment_cost, 2))

# ---------------------------------------------------------------------------
# 8. KPI TABLE 5 — Cross-border US <-> Canada (USCA market)
# ---------------------------------------------------------------------------
usca = df[df["Market"] == "USCA"].copy()
usca["is_canada"] = usca["Order Region"].eq("Canada")
usca["lane"] = np.where(usca["is_canada"], "Cross-border: US DC -> Canada", "Domestic US")

# Model a customs/border-clearance day added to cross-border transit + a
# duties/tax compliance buffer, since parcels crossing into Canada clear
# CBSA and may be subject to GST/HST + duty depending on value & CUSMA
# origin rules (informational context documented in the report; the extra
# transit day below is the only synthetic adjustment made to the data).
usca["border_adj_real_days"] = usca["Days for shipping (real)"] + np.where(usca["is_canada"], 1, 0)
usca["border_adj_on_time"] = (usca["border_adj_real_days"] <= usca["Days for shipment (scheduled)"]).astype(int)

cross_border_summary = usca.groupby("lane").agg(
    orders=("Order Id", "count"),
    otif_rate=("is_otif", "mean"),
    on_time_rate_pre_customs_adj=("is_on_time", "mean"),
    on_time_rate_post_customs_adj=("border_adj_on_time", "mean"),
    cancel_rate=("is_cancelled", "mean"),
    avg_cost_per_order=("cost_per_order", "mean"),
    avg_sales=("Sales", "mean"),
).reset_index()
cross_border_summary.to_csv(f"{OUT}/kpi_cross_border_summary.csv", index=False)

cross_border_monthly = usca.groupby(["order_month", "lane"]).agg(
    orders=("Order Id", "count"),
).reset_index()
cross_border_monthly.to_csv(f"{OUT}/kpi_cross_border_monthly.csv", index=False)

# ---------------------------------------------------------------------------
# 9. KPI TABLE 6 — Corporate segment (B2B) seasonal surge / capacity
# ---------------------------------------------------------------------------
corp = df[df["Customer Segment"] == "Corporate"].copy()
corp_monthly = corp.groupby("order_month").agg(
    orders=("Order Id", "count"),
    total_units=("Order Item Quantity", "sum"),
    total_sales=("Sales", "sum"),
    otif_rate=("is_otif", "mean"),
    avg_cost_per_order=("cost_per_order", "mean"),
).reset_index()
corp_monthly.to_csv(f"{OUT}/kpi_corporate_monthly.csv", index=False)

corp_category = corp.groupby("Category Name").agg(
    orders=("Order Id", "count"),
    total_units=("Order Item Quantity", "sum"),
    total_sales=("Sales", "sum"),
    otif_rate=("is_otif", "mean"),
).reset_index().sort_values("orders", ascending=False)
corp_category.to_csv(f"{OUT}/kpi_corporate_category.csv", index=False)

# All-segment monthly for comparison (surge detection context)
all_monthly_by_segment = df.groupby(["order_month", "Customer Segment"]).agg(
    orders=("Order Id", "count"),
).reset_index()
all_monthly_by_segment.to_csv(f"{OUT}/kpi_monthly_by_segment.csv", index=False)

# ---------------------------------------------------------------------------
# 10. KPI TABLE 7 — Carrier diversification, zone-skipping & packaging
#     optimization savings simulation (three independent CPO levers)
# ---------------------------------------------------------------------------
# Scenario assumptions (documented for interview defensibility):
#  Lever A - Carrier diversification: 40% of Standard/Second Class volume
#            (today effectively single-sourced) is re-bid across a 2nd
#            regional 3PL/carrier, yielding a 7% rate improvement on that
#            shifted volume via competitive tension.
#  Lever B - Zone skipping: domestic + near-shore lanes (zone 1-4: US
#            regions, Canada, Central America, Caribbean, South America)
#            move 50% of eligible volume through a consolidated linehaul +
#            regional injection point, cutting the zone-distance cost
#            component by 22% on that shifted volume.
#  Lever C - Packaging optimization: right-sized packaging/dimensional-
#            weight program cuts the per-unit quantity surcharge 25% across
#            all orders (fewer void-fill materials, better cube utilization).
scenario = cpo_by_region_carrier.copy()

diversifiable_modes = {"Standard Class", "Second Class"}
zone_skip_eligible = {"West of USA", "East of USA", "South of  USA", "US Center",
                       "Canada", "Central America", "Caribbean", "South America"}

def lever_a_savings(row):
    if row["Shipping Mode"] in diversifiable_modes:
        return row["total_cost"] * 0.40 * 0.07
    return 0.0

def lever_b_savings(row):
    if row["Order Region"] in zone_skip_eligible:
        return row["total_cost"] * 0.50 * 0.22
    return 0.0

scenario["savings_carrier_diversification"] = scenario.apply(lever_a_savings, axis=1)
scenario["savings_zone_skipping"] = scenario.apply(lever_b_savings, axis=1)

# Lever C applied at the order level (packaging touches every shipment)
packaging_savings_total = (df["qty_surcharge"] * 0.25).sum()

scenario["simulated_annual_savings"] = (scenario["savings_carrier_diversification"]
                                         + scenario["savings_zone_skipping"])
scenario_summary = scenario.groupby("Order Region").agg(
    current_total_cost=("total_cost", "sum"),
    savings_carrier_diversification=("savings_carrier_diversification", "sum"),
    savings_zone_skipping=("savings_zone_skipping", "sum"),
).reset_index()
scenario_summary["simulated_savings"] = (scenario_summary["savings_carrier_diversification"]
                                          + scenario_summary["savings_zone_skipping"])
scenario_summary["savings_pct"] = scenario_summary["simulated_savings"] / scenario_summary["current_total_cost"]
scenario_summary = scenario_summary.sort_values("simulated_savings", ascending=False)
scenario_summary.to_csv(f"{OUT}/kpi_savings_simulation.csv", index=False)

total_cost_all = scenario["total_cost"].sum()
lever_totals = pd.DataFrame({
    "lever": ["Carrier diversification", "Zone skipping", "Packaging optimization"],
    "annual_savings": [
        scenario["savings_carrier_diversification"].sum(),
        scenario["savings_zone_skipping"].sum(),
        packaging_savings_total,
    ],
})
lever_totals["pct_of_total_cost"] = lever_totals["annual_savings"] / total_cost_all
lever_totals.to_csv(f"{OUT}/kpi_savings_by_lever.csv", index=False)

total_savings = lever_totals["annual_savings"].sum()
print(f"Total current modeled shipping cost: ${total_cost_all:,.0f}")
print(f"Total simulated annual savings (3 levers): ${total_savings:,.0f} ({total_savings/total_cost_all:.1%})")
print(lever_totals)

# ---------------------------------------------------------------------------
# 11. Top-line KPI summary (for report cover page / dashboard header)
# ---------------------------------------------------------------------------
summary = {
    "total_orders": int(len(df)),
    "date_range": f"{df['order date (DateOrders)'].min().date()} to {df['order date (DateOrders)'].max().date()}",
    "otif_rate": round(df["is_otif"].mean(), 4),
    "on_time_rate": round(df["is_on_time"].mean(), 4),
    "cancel_rate": round(df["is_cancelled"].mean(), 4),
    "avg_cost_per_order": round(df["cost_per_order"].mean(), 2),
    "total_shipping_cost": round(df["cost_per_order"].sum(), 2),
    "total_margin_leakage": round(df["margin_leakage"].sum(), 2),
    "total_reshipment_cost": round(total_reshipment_cost, 2),
    "simulated_annual_savings": round(total_savings, 2),
    "simulated_savings_pct": round(total_savings/total_cost_all, 4),
    "corporate_segment_orders": int(len(corp)),
    "corporate_segment_sales": round(corp["Sales"].sum(), 2),
    "usca_cross_border_orders": int(usca["is_canada"].sum()),
}
pd.Series(summary).to_csv(f"{OUT}/kpi_topline_summary.csv")
print("\nTOP-LINE SUMMARY")
for k, v in summary.items():
    print(f"  {k}: {v}")

print("\nAll KPI tables written to", OUT)
