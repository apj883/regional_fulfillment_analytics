# Regional Outbound Fulfillment & Logistics Analytics

A portfolio project simulating the full analytics scope of a Regional Supply Chain / Fulfillment Operations Analyst role: 3PL SLA management, Cost-per-Order reduction, OTIF tracking, EDD accuracy, failed-delivery root cause, cross-border US↔Canada distribution, and B2B seasonal-surge planning.

## Data source

**DataCo Smart Supply Chain Dataset** (Kaggle, `kagglehub` id: `shashwatwork/dataco-smart-supply-chain-for-big-data-analysis`). 180,519 raw order-line records / 53 fields / Jan 2015–Jan 2018, a global sporting-goods/apparel retailer selling into 5 markets across Consumer, Corporate, and Home Office segments. 178,626 orders remained after excluding fraud-hold/payment-review rows that never physically shipped.

**Product-focus decision:** the Corporate (B2B) customer segment was used as the lens for the seasonal-surge / new-launch section (Section 7 of the report), per project scoping — 54,222 orders, $11.05M in sales.

## Files in this delivery

| File | What it is |
|---|---|
| `Regional_Outbound_Fulfillment_Case_Study.docx` / `.pdf` | The full 19-page case study report — methodology, findings, and recommendations mapped to every responsibility of the role |
| `dashboard.html` | Interactive Plotly dashboard — open directly in any browser, no server needed |
| `Regional_Fulfillment_KPI_Workbook.xlsx` | Full KPI data workbook, 10 sheets, live formulas, zero errors |
| `01_etl_kpi_engineering.py` | Python ETL + KPI engineering (loads raw data, builds the cost model, computes every KPI) |
| `02_charts.py` | Generates all report charts (matplotlib) |
| `03_dashboard.py` | Generates the interactive dashboard (Plotly) |
| `04_build_workbook.py` | Generates the Excel KPI workbook (openpyxl) |
| `build_report.js` | Generates the Word report (docx-js) |
| `charts/` | All 11 report chart PNGs |


## Reproducing the analysis

```bash
pip install pandas numpy matplotlib plotly kagglehub openpyxl xlsxwriter
python3 01_etl_kpi_engineering.py   # -> writes KPI CSVs
python3 02_charts.py                # -> writes chart PNGs
python3 03_dashboard.py             # -> writes dashboard.html
python3 04_build_workbook.py        # -> writes the Excel workbook
# Word report: npm install docx, then `node build_report.js`
```

## Why the numbers include a cost model

No public dataset exposes real carrier invoices — that data is confidential to every retailer and 3PL. Cost per Order, margin leakage, and the savings simulation are built on a transparent, fully documented parcel-pricing model layered over real operational fields (shipping mode, scheduled vs. actual transit days, region, order value, quantity). Every assumption is listed in Appendix A of the report. This is standard practice for a modeling exercise built on public data — the same approach an analyst would use to estimate cost impact before a carrier rate card is finalized.

## Headline findings

- **OTIF: 40.9%** network-wide (target: 90%+)
- **First Class carrier: 0% OTIF** despite costing 2.1x Standard Class — the single clearest SLA renegotiation target in the data
- **$1.82M in shipping margin leakage**, concentrated in Western Europe, Central America, and South America
- **$219K in simulated annual savings (5.9%)** from a 3-lever plan: carrier diversification, zone skipping, packaging optimization
- **Cross-border US→Canada**: on-time rate drops from 48.1% to 30.4% once a realistic customs-clearance buffer is modeled in — current EDD promises to Canadian customers likely overstate reliability
