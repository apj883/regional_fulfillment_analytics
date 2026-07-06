const fs = require("fs");
const path = require("path");
const sizeOf = (() => {
  // minimal PNG size reader (no extra deps)
  return function (buf) {
    return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  };
})();
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Header, Footer, AlignmentType, LevelFormat, ExternalHyperlink, InternalHyperlink,
  BookmarkStart, BookmarkEnd,
  HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak, TabStopType, TabStopPosition,
  PositionalTab, PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader,
} = require("docx");

const CHARTS = "/sessions/serene-amazing-cori/work/charts";

// Page numbers for the static Table of Contents. First build pass uses
// placeholders; after rendering, these are patched with real page numbers
// read from the generated PDF (see build_toc_pages.py) and the doc is
// rebuilt so the printed TOC matches actual pagination.
let PAGES = {
  sec_exec_summary: 3, sec_role_scope: 4, sec_methodology: 5, sec_otif: 6,
  sec_cpo: 8, sec_dashboard: 9, sec_surge: 10, sec_edd: 11,
  sec_failed_delivery: 12, sec_vendor: 13, sec_cross_border: 14,
  sec_savings: 15, sec_appendix: 16,
};
try {
  const override = JSON.parse(fs.readFileSync("/sessions/serene-amazing-cori/work/dashboard/toc_pages.json", "utf8"));
  PAGES = { ...PAGES, ...override };
} catch (e) { /* use placeholders on first pass */ }
const NAVY = "2B2620", TEAL = "4B6B43", CORAL = "C1592E", LIGHTBLUE = "F2E9DC", LIGHTGREY = "F2F2F2";

function img(name, targetWidth) {
  const p = path.join(CHARTS, name);
  const buf = fs.readFileSync(p);
  const { width, height } = sizeOf(buf);
  const w = targetWidth;
  const h = Math.round((height / width) * w);
  return new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h },
    altText: { title: name, description: name, name: name } });
}

let _bookmarkLinkId = 100; // shared counter — docx-js's own Bookmark wrapper resets to 1
                            // per instance, which produces duplicate w:id values across
                            // multiple bookmarks, so BookmarkStart/BookmarkEnd are built
                            // directly here with a manually incremented, document-unique id.
function h1(text, anchor) {
  const children = anchor
    ? [new BookmarkStart(anchor, _bookmarkLinkId), new TextRun(text), new BookmarkEnd(_bookmarkLinkId++)]
    : [new TextRun(text)];
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
}
function tocEntry(title, anchor, page) {
  return new Paragraph({
    spacing: { after: 130 },
    children: [
      new InternalHyperlink({
        anchor,
        children: [new TextRun({ text: title, color: TEAL, underline: {} })],
      }),
      new TextRun({
        children: [
          new PositionalTab({
            alignment: PositionalTabAlignment.RIGHT,
            relativeTo: PositionalTabRelativeTo.MARGIN,
            leader: PositionalTabLeader.DOT,
          }),
          String(page),
        ],
      }),
    ],
  });
}
function p(text, opts = {}) {
  return new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text, ...opts })] });
}
function pRuns(runs, opts = {}) {
  return new Paragraph({ spacing: { after: 160 }, ...opts, children: runs });
}
function bullet(text, bold_lead) {
  const children = bold_lead
    ? [new TextRun({ text: bold_lead, bold: true }), new TextRun({ text })]
    : [new TextRun({ text })];
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 90 }, children });
}
function caption(text) {
  return new Paragraph({ spacing: { after: 220, before: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, italics: true, size: 18, color: "555555" })] });
}
function imgPara(name, targetWidth = 580) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, children: [img(name, targetWidth)] });
}
function calloutBox(title, text) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: 9360, type: WidthType.DXA },
      shading: { fill: "FDF3E7", type: ShadingType.CLEAR },
      borders: {
        top: { style: BorderStyle.SINGLE, size: 4, color: CORAL },
        bottom: { style: BorderStyle.SINGLE, size: 4, color: CORAL },
        left: { style: BorderStyle.SINGLE, size: 4, color: CORAL },
        right: { style: BorderStyle.SINGLE, size: 4, color: CORAL },
      },
      margins: { top: 140, bottom: 140, left: 180, right: 180 },
      children: [
        new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: title, bold: true, color: "7A2E38", size: 21 })] }),
        new Paragraph({ children: [new TextRun({ text, size: 21 })] }),
      ],
    })] })],
  });
}

function kpiTable(rows, colWidths) {
  const total = colWidths.reduce((a, b) => a + b, 0);
  const headerRow = new TableRow({
    tableHeader: true,
    children: rows[0].map((cell, i) => new TableCell({
      width: { size: colWidths[i], type: WidthType.DXA },
      shading: { fill: NAVY, type: ShadingType.CLEAR },
      margins: { top: 90, bottom: 90, left: 120, right: 120 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ children: [new TextRun({ text: cell, bold: true, color: "FFFFFF", size: 19 })] })],
    })),
  });
  const border = { style: BorderStyle.SINGLE, size: 2, color: "D0D0D0" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const bodyRows = rows.slice(1).map((r, ri) => new TableRow({
    children: r.map((cell, i) => new TableCell({
      width: { size: colWidths[i], type: WidthType.DXA },
      borders,
      shading: { fill: ri % 2 === 0 ? "FFFFFF" : LIGHTGREY, type: ShadingType.CLEAR },
      margins: { top: 70, bottom: 70, left: 120, right: 120 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ children: [new TextRun({ text: String(cell), size: 19 })] })],
    })),
  }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: colWidths, rows: [headerRow, ...bodyRows] });
}

function divider() {
  return new Paragraph({ spacing: { before: 100, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC", space: 1 } }, children: [] });
}

// ---------------------------------------------------------------------
// CONTENT
// ---------------------------------------------------------------------

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial", color: NAVY },
        paragraph: { spacing: { before: 380, after: 200 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: TEAL, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: NAVY },
        paragraph: { spacing: { before: 240, after: 140 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1350, right: 1440, bottom: 1350, left: 1440 } },
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "Regional Outbound Fulfillment & Logistics Analytics", size: 16, color: "888888" })],
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Page ", size: 16, color: "888888" }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })],
      })] }),
    },
    children: [
      // ---------------- TITLE PAGE ----------------
      new Paragraph({ spacing: { before: 1400 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "REGIONAL OUTBOUND FULFILLMENT", bold: true, size: 44, color: NAVY })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
        children: [new TextRun({ text: "& LOGISTICS ANALYTICS", bold: true, size: 44, color: NAVY })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 500 },
        children: [new TextRun({ text: "A Data-Driven Case Study in 3PL SLA Management, Cost-per-Order Optimization,\nOTIF Performance, and Cross-Border (US → Canada) Distribution",
          italics: true, size: 24, color: TEAL, break: 1 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 300 },
        children: [new TextRun({ text: "Prepared by Aman", size: 22, bold: true })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
        children: [new TextRun({ text: "Regional Supply Chain & Fulfillment Operations Analyst — Portfolio Project", size: 20, color: "555555" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "July 2026", size: 20, color: "555555" })] }),
      new Paragraph({ spacing: { before: 700 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Dataset: DataCo Smart Supply Chain (Kaggle) — 178,626 orders — Jan 2015–Jan 2018", size: 18, color: "777777" })] }),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- TOC ----------------
      h1("Table of Contents"),
      tocEntry("1. Executive Summary", "sec_exec_summary", PAGES.sec_exec_summary),
      tocEntry("2. Role Scope → Analysis Mapping", "sec_role_scope", PAGES.sec_role_scope),
      tocEntry("3. Data & Methodology", "sec_methodology", PAGES.sec_methodology),
      tocEntry("4. Outbound Operations & 3PL SLA Performance", "sec_otif", PAGES.sec_otif),
      tocEntry("5. Cost per Order & Margin Leakage", "sec_cpo", PAGES.sec_cpo),
      tocEntry("6. Fulfillment Analytics Dashboard", "sec_dashboard", PAGES.sec_dashboard),
      tocEntry("7. New Launches & Seasonal Surge Planning (Corporate / B2B Segment)", "sec_surge", PAGES.sec_surge),
      tocEntry("8. Outbound Routing Guide & EDD Accuracy", "sec_edd", PAGES.sec_edd),
      tocEntry("9. Failed Delivery & Reshipment Root-Cause", "sec_failed_delivery", PAGES.sec_failed_delivery),
      tocEntry("10. Vendor Negotiation & Team Enablement", "sec_vendor", PAGES.sec_vendor),
      tocEntry("11. Reverse Logistics & Cross-Border US–Canada Distribution", "sec_cross_border", PAGES.sec_cross_border),
      tocEntry("12. Cost Reduction Roadmap", "sec_savings", PAGES.sec_savings),
      tocEntry("Appendix A: Full Methodology & Assumptions", "sec_appendix", PAGES.sec_appendix),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- EXEC SUMMARY ----------------
      h1("1. Executive Summary", "sec_exec_summary"),
      p("This project simulates the analytics function behind a regional outbound fulfillment operation for a global sporting-goods/apparel retailer, using 178,626 real orders (Jan 2015–Jan 2018) from the DataCo Smart Supply Chain dataset. The goal: build the same KPI stack, cost model, and decision-support analysis a Regional Fulfillment Operations Analyst would own — 3PL SLA compliance, cost per order, OTIF, EDD accuracy, failed-delivery root cause, cross-border US–Canada performance, and B2B seasonal-surge planning — end to end, from raw data to an executive-ready dashboard and savings roadmap."),
      p("Key findings:"),
      bullet("network-wide, well below the 90%+ target typical for retail fulfillment operations — driven almost entirely by one carrier tier (see Finding #1 below).", "OTIF sits at 40.9% "),
      bullet("First Class shipping has a 0% OTIF rate — every single First Class order in three years arrived after its promised window, despite it costing 2.1x Standard Class per order ($31.46 vs. $15.03).", "Finding #1: "),
      bullet("across the modeled $3.74M annual outbound shipping spend, with the highest concentration in Western Europe, Central America, and South America.", "Shipping margin leakage totals ~$1.82M "),
      bullet("across carrier diversification, zone skipping, and packaging optimization — a 5.9% reduction in total outbound shipping cost.", "A three-lever cost-reduction plan captures $219k in simulated annual savings "),
      bullet("Canada-bound orders look on-time at the carrier-scan level (48.1%) but fall to 30.4% once a realistic customs-clearance buffer is applied — meaning current EDD promises to Canadian customers likely overstate real transit reliability.", "Cross-border (US→Canada): "),
      bullet("with a clear seasonal surge pattern that should drive capacity and staffing planning ahead of peak months.", "The Corporate (B2B) segment represents 54,222 orders and $11.05M in sales "),
      p("Deliverables produced: this report, an interactive KPI dashboard (dashboard.html), a full KPI data workbook (Excel), the underlying Python ETL/analysis code, and a LinkedIn-ready project summary."),

      // ---------------- SCOPE MAPPING ----------------
      h1("2. Role Scope → Analysis Mapping", "sec_role_scope"),
      p("Each analytical thread below was purpose-built to mirror a specific responsibility of a Regional Outbound Fulfillment Operations Analyst role:"),
      kpiTable([
        ["Role Responsibility", "Where It's Addressed"],
        ["Lead outbound ops; 3PL SLA compliance (processing, packaging, carrier handoff)", "Section 4 — OTIF & Carrier SLA Performance"],
        ["Own fulfillment/shipping budget; reduce Cost per Order (zone skipping, carrier diversification, packaging)", "Section 5 — Cost per Order & Margin Leakage; Section 9 — Savings Roadmap"],
        ["Direct fulfillment analytics; dashboards for OTIF & margin leakage", "Section 6 — Analytics Dashboard"],
        ["Model costs for launches/seasonal surges; prep regional infrastructure", "Section 7 — B2B Segment Seasonal Surge Planning"],
        ["Evolve routing guides; carrier selection vs. EDD", "Section 8 — EDD Accuracy & Routing Guide"],
        ["Analyze failed deliveries; reduce reshipment cost", "Section 9 — Failed Delivery Root-Cause (Pareto)"],
        ["Mentor coordinators; use data to negotiate with vendors", "Section 10 — Vendor Negotiation & Team Enablement"],
        ["Reverse logistics & cross-border (US→Canada); tax compliance & transit time", "Section 11 — Cross-Border US–Canada Distribution"],
      ], [4680, 4680]),

      // ---------------- METHODOLOGY ----------------
      h1("3. Data & Methodology", "sec_methodology"),
      h2("3.1 Dataset"),
      p("DataCo Smart Supply Chain Dataset (Kaggle, kagglehub id: shashwatwork/dataco-smart-supply-chain-for-big-data-analysis). 180,519 raw order-line records, 53 fields, spanning Jan 2015 – Jan 2018, covering a global sporting-goods/apparel retailer selling into 5 markets (LATAM, Europe, Pacific Asia, USCA, Africa) across Consumer, Corporate, and Home Office customer segments. After removing pure fraud-hold/payment-review rows that never physically shipped, 178,626 orders remained for analysis."),
      h2("3.2 Why a cost model was necessary"),
      p("No public dataset exposes real carrier invoices — that data is contractually confidential to every retailer and 3PL. To produce Cost-per-Order, margin-leakage, and savings-simulation KPIs, a transparent, documented cost model was layered on top of the real operational fields (shipping mode, scheduled vs. actual transit days, region, order value, quantity). This mirrors how a real analyst would model “what-if” cost scenarios before a rate card is finalized. All formulas and assumptions are listed in the Appendix so every number in this report can be reproduced or challenged."),
      h2("3.3 Core KPI definitions"),
      bullet("Delivered on/before the scheduled transit window AND the order was not cancelled.", "OTIF (On-Time In-Full): "),
      bullet("Modeled outbound parcel cost = base rate by service level × regional zone factor + per-unit quantity surcharge + invoice-variance noise.", "Cost per Order (CPO): "),
      bullet("Modeled shipping cost minus a 6%-of-sales “healthy” shipping-cost target, summed across orders exceeding that target.", "Shipping Margin Leakage: "),
      bullet("Actual transit days ≤ scheduled transit days (i.e., the promised delivery date to the customer was met).", "EDD Met: "),
      bullet("Orders cancelled or flagged “Shipping canceled”; each carries a full re-ship cost.", "Failed Delivery / Reshipment: "),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 4: OTIF ----------------
      h1("4. Outbound Operations & 3PL SLA Performance", "sec_otif"),
      p("Shipping Mode (Standard / Second / First Class / Same Day) is used as the carrier/service-level proxy in this dataset. OTIF and on-time rates were computed per tier to evaluate whether current 3PL/carrier SLA commitments are actually being met."),
      imgPara("01_otif_by_carrier.png", 520),
      caption("Figure 1. OTIF rate by carrier / service tier vs. network average (40.9%)."),
      calloutBox("Finding: First Class is structurally broken.",
        "First Class carries the highest per-order cost ($31.46, ~2.1x Standard Class) and the tightest promise (1 scheduled day) — yet realizes a 0% OTIF rate; average actual transit is 2.0 days, double what's promised. This is not noise: it holds across all three years of data. Recommendation: either renegotiate the First Class scheduled-day commitment with the carrier to match real network capability, or move First Class volume to a carrier proven to hit 1-day service."),
      imgPara("02_otif_monthly_trend.png", 580),
      caption("Figure 2. OTIF has been essentially flat (38–43%) for three years — this is a systemic network issue, not a seasonal blip."),
      kpiTable([
        ["Carrier / Service Tier", "Orders", "OTIF Rate", "Avg. Transit Variance (days)", "Avg. Cost/Order"],
        ["Standard Class", "106,654", "57.6%", "0.00", "$15.03"],
        ["Second Class", "34,830", "19.3%", "+1.99", "$21.98"],
        ["First Class", "27,499", "0.0%", "+1.00", "$31.46"],
        ["Same Day", "9,643", "49.6%", "+0.48", "$52.44"],
      ], [2400, 1500, 1500, 2160, 1800]),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 5: COST PER ORDER ----------------
      h1("5. Cost per Order & Margin Leakage", "sec_cpo"),
      p("Total modeled outbound shipping spend across the analysis window is $3.74M, averaging $20.93/order. Cost concentration is heavily international: Western Europe, Central America, and South America together represent the largest share of total outbound cost, driven by zone-distance pricing on a single-node US fulfillment network."),
      imgPara("03_cost_per_order_by_region.png", 560),
      caption("Figure 3. Total outbound shipping cost by region (top 12). International/near-shore zones dominate spend."),
      imgPara("04_margin_leakage_by_region.png", 560),
      caption("Figure 4. Shipping margin leakage — cost per order in excess of a 6%-of-sales target — totals $1.82M, concentrated in the same high-zone-cost regions."),
      p("Because margin leakage tracks cost concentration almost 1:1, the fix is the same lever set used in Section 9: reduce the effective zone cost through zone skipping and carrier diversification, and reduce the fixed per-unit surcharge through packaging optimization."),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 6: DASHBOARD ----------------
      h1("6. Fulfillment Analytics Dashboard", "sec_dashboard"),
      p("A live, interactive HTML dashboard (dashboard.html, included with this project) was built in partnership-style with a mock “Data/Systems” handoff: KPI cards up top (OTIF, Cost per Order, Margin Leakage, Reshipment Cost, Simulated Savings, Cross-Border Volume) followed by drill-down charts for every KPI in this report. It is fully self-contained (Plotly + static HTML) so it can be opened directly in a browser or embedded in an internal wiki/BI tool without a server."),
      bullet("Real-time-style KPI cards for OTIF, Cost per Order, and Margin Leakage — the three metrics an ops lead needs at a glance every morning.", "Design choice 1: "),
      bullet("Every chart pairs a volume/cost metric with a rate metric (e.g., failed orders + cumulative % in the Pareto view) so root cause and impact are always visible together.", "Design choice 2: "),
      bullet("dual-axis charts for EDD and Pareto views make it trivial to spot where a small carrier count drives a large share of the problem.", "Design choice 3: "),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 7: SEASONAL SURGE ----------------
      h1("7. New Launches & Seasonal Surge Planning (Corporate / B2B Segment)", "sec_surge"),
      p("Per the product-focus decision for this project, the Corporate customer segment (bulk/wholesale-style B2B ordering, 54,222 orders, $11.05M in sales) was used as the lens for surge and capacity planning — the same discipline that applies to a new product launch: forecast the volume spike, flag the months that will break current capacity, and align packaging/handling ahead of time."),
      imgPara("09_corporate_seasonal_surge.png", 580),
      caption("Figure 5. Corporate segment order volume by month. Months exceeding the mean + 1 standard deviation are flagged as surge months requiring pre-built capacity (temp labor, extra carrier pickups, packaging stock)."),
      imgPara("11_corporate_category_mix.png", 560),
      caption("Figure 6. Category mix within the Corporate segment — Cleats, Indoor/Outdoor Games, and Women's Apparel lead by unit volume, informing which SKUs need surge-ready packaging and slotting."),
      p("Recommendation: build the regional capacity plan (temp staffing, dock appointments, packaging inventory) around the flagged surge months above, with a 4–6 week lead time, and pressure-test it against the highest-volume Corporate categories shown in Figure 6."),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 8: EDD & ROUTING ----------------
      h1("8. Outbound Routing Guide & EDD Accuracy", "sec_edd"),
      p("A routing guide should route each shipment to the carrier/service tier that hits the promised Estimated Delivery Date (EDD) at the lowest cost. Today's data shows that promise and reality are misaligned for two of four tiers."),
      imgPara("05_edd_accuracy_by_carrier.png", 540),
      caption("Figure 7. EDD-met rate (bars) vs. average transit variance in days (line) by carrier tier. Standard Class is the only tier that reliably meets its promise; Second Class and First Class both run ~1–2 days over their scheduled window."),
      bullet("Standard Class (60.2% EDD-met, ~0 variance) should remain the default routing choice for non-urgent freight — it is both the cheapest and most schedule-reliable tier.", "Routing guide update 1: "),
      bullet("Second Class and First Class scheduled-day commitments should be renegotiated upward by 1–2 days to match actual carrier performance, rather than continuing to promise customers a date the network doesn't hit.", "Routing guide update 2: "),
      bullet("volume should only be routed there when the +$31–$52 premium is justified by genuine customer urgency, given current reliability.", "Same Day and First Class carry the highest cost-to-reliability mismatch — "),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 9: FAILED DELIVERY ----------------
      h1("9. Failed Delivery & Reshipment Root-Cause", "sec_failed_delivery"),
      p("4.3% of all orders (7,650) were cancelled or marked “Shipping canceled,” driving a modeled $163k in annual reshipment cost. Root-causing by region and category surfaces where corrective action will have the most impact."),
      imgPara("06_failed_delivery_pareto_region.png", 560),
      caption("Figure 8. Failed-delivery Pareto by region — the top 3 regions (Western Europe, Central America, South America) account for ~41% of all failed deliveries."),
      imgPara("07_failed_delivery_by_category.png", 560),
      caption("Figure 9. Failed-delivery Pareto by product category — Cleats, Men's Footwear, and Women's Apparel are the top three, consistent with their overall order-volume share (i.e., failure rate is roughly proportional to volume, not category-specific risk)."),
      p("Because failure rate is roughly volume-proportional rather than concentrated in one “problem” category, the fix is regional/process-level (carrier handoff quality, address-verification, fraud-review speed in the top 3 regions) rather than a packaging redesign for a specific product line."),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 10: VENDOR NEGOTIATION / MENTORSHIP ----------------
      h1("10. Vendor Negotiation & Team Enablement", "sec_vendor"),
      p("The analytics above are built to double as negotiation and coaching material — the two vendor-facing and people-facing responsibilities of the role."),
      h2("10.1 Using the data in a carrier negotiation"),
      bullet("First Class carrier is being paid a premium rate for a 0% OTIF outcome — the single clearest, most defensible renegotiation opener in this dataset.", "Leverage point 1: "),
      bullet("40% of Standard/Second Class volume is effectively single-sourced; introducing a competing regional carrier on that volume is modeled to save $66k/year purely from competitive tension, with no service-level change required.", "Leverage point 2: "),
      bullet("in the top-cost, highest zone-factor regions creates negotiating room for consolidated-linehaul or regional-injection pricing (modeled savings: $97k/year).", "Leverage point 3: "),
      h2("10.2 Coaching junior coordinators"),
      p("The recommended coaching sequence, using this same project as the training case:"),
      bullet("before proposing a fix — e.g., “First Class is expensive” is an opinion; “First Class has a 0% OTIF across 27,499 orders and 3 years” is a fact a vendor cannot dispute.", "Start from the number, not the anecdote: "),
      bullet("— a region with 50 failed orders and $50k reshipment cost matters more than a region with 500 failed orders and $2k reshipment cost.", "Always pair a rate with an impact figure "),
      bullet("before it becomes a headline metric — juniors should be able to explain exactly how OTIF, EDD-met, and Cost per Order are computed, the same way this report's Appendix does.", "Show your formula "),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 11: CROSS BORDER ----------------
      h1("11. Reverse Logistics & Cross-Border US–Canada Distribution", "sec_cross_border"),
      p("The USCA market segment (25,799 orders) splits into Domestic US (24,561 orders) and Canada-bound cross-border shipments (958 orders). At face value, cross-border performance looks comparable to — even slightly better than — domestic. But that comparison ignores a critical real-world step: Canada Border Services Agency (CBSA) clearance."),
      imgPara("08_cross_border_us_canada.png", 560),
      caption("Figure 10. Domestic US vs. cross-border US→Canada performance. The customs-adjusted on-time rate (a modeled +1 day CBSA clearance buffer applied to Canada-bound orders only) drops from 48.1% to 30.4%, while domestic stays flat at 42.8%."),
      calloutBox("Why the +1 day adjustment matters",
        "The raw dataset has no customs field — it was captured from a US-centric order system that doesn't model border clearance. In reality, cross-border parcels into Canada are subject to CBSA processing and, depending on value and origin under CUSMA rules, may incur GST/HST and duty, both of which add clearance time beyond the carrier's US-side transit scan. Applying even a conservative 1-day buffer flips the read from “cross-border performs fine” to “cross-border EDD promises are likely overstated by 15+ points.” This is exactly the kind of gap a regional analyst should catch before a customer-facing EDD commitment goes live."),
      h2("11.1 Tax & compliance considerations (qualitative)"),
      bullet("Low-value shipments may qualify for Canada's CAD $150 duty-free / CAD $40 tax-free thresholds under the Canada–US–Mexico Agreement (CUSMA); shipments above those thresholds are subject to duty and GST/HST collected at the border or by the carrier on delivery.", "Duty & tax exposure: "),
      bullet("choosing a carrier with Canadian customs brokerage bundled into the outbound rate reduces both transit-time risk and the customer-experience risk of a surprise duty bill on delivery.", "Broker model: "),
      bullet("reverse logistics into Canada should route returns through a bonded/registered process to avoid double duty payment — duty drawback or exemption documentation should be a routing-guide checkbox, not an afterthought.", "Reverse logistics angle: "),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- SECTION 12: SAVINGS ROADMAP ----------------
      h1("12. Cost Reduction Roadmap", "sec_savings"),
      p("Three independent, stackable levers were modeled against the current $3.74M outbound shipping base:"),
      imgPara("10_savings_by_lever.png", 520),
      caption("Figure 11. Simulated annual savings by lever: $219k combined (5.9% of total outbound shipping cost)."),
      kpiTable([
        ["Lever", "Mechanism", "Simulated Annual Savings", "% of Total Cost"],
        ["Zone Skipping", "Consolidated linehaul + regional injection on 50% of eligible domestic/near-shore volume, 22% cost cut on that volume", "$97,486", "2.6%"],
        ["Carrier Diversification", "Competitive re-bid on 40% of Standard/Second Class volume, 7% rate improvement", "$66,311", "1.8%"],
        ["Packaging Optimization", "Right-sized packaging cuts per-unit surcharge 25% network-wide", "$55,370", "1.5%"],
      ], [2400, 4200, 1800, 960]),
      p("Sequencing recommendation: launch packaging optimization first (fastest to implement, no carrier contract changes), run the carrier-diversification RFP in parallel (60–90 day cycle), and use the resulting competitive quotes as the anchor for a zone-skipping / regional-injection pilot in the top 3 highest-cost regions identified in Figure 3."),

      // ---------------- APPENDIX ----------------
      h1("Appendix A: Full Methodology & Assumptions", "sec_appendix"),
      h2("A.1 Cost model formulas"),
      bullet("$6.50 / $9.75 / $14.25 / $24.00 for Standard / Second / First Class / Same Day respectively (approximates 2016-era US domestic parcel tiers, consistent with the Shipping Mode distribution in the data).", "Base rate by service level: "),
      bullet("1.00 for US-domestic regions, 1.35 for Canada, 1.45–1.75 for Central/South America & Caribbean, 2.30–2.80 for Europe/Asia/Africa/Oceania — approximates distance-banded parcel-zone pricing from a single US-Midwest fulfillment center.", "Zone factor by Order Region: "),
      bullet("$1.10 per unit above the first unit in the order.", "Quantity surcharge: "),
      bullet("modeled_shipping_cost = (base_rate × zone_factor) + qty_surcharge + N(0, 0.6) noise, floored at $2.50.", "Full formula: "),
      bullet("modeled_shipping_cost − (6% × Sales), floored at $0.", "Margin leakage per order: "),
      h2("A.2 Savings simulation assumptions"),
      bullet("40% of Standard/Second Class volume re-bid at a 7% rate improvement.", "Carrier diversification: "),
      bullet("50% of eligible domestic/near-shore volume shifted to consolidated linehaul at 22% cost reduction on that volume.", "Zone skipping: "),
      bullet("25% reduction in the per-unit quantity surcharge, applied network-wide.", "Packaging optimization: "),
      h2("A.3 Known limitations"),
      bullet("Cost, margin-leakage, and savings figures are directional/illustrative, built on a transparent public-parameter model layered over real operational data — not actual carrier invoices (which are never public).", ""),
      bullet("The dataset itself has known synthetic characteristics (e.g., Late_delivery_risk correlates near-perfectly with Shipping Mode for some tiers), which is why Finding #1 (First Class 0% OTIF) is stated as a data-driven observation rather than assumed to reflect any specific real-world carrier.", ""),
      bullet("The +1 day CBSA customs buffer is a conservative, documented estimate for illustrative purposes, not sourced from actual CBSA processing-time data.", ""),
      h2("A.4 Tools & data source"),
      bullet("Python 3.10 (pandas, numpy) for ETL and KPI engineering.", ""),
      bullet("Plotly for the interactive HTML dashboard; Matplotlib for report-embedded charts.", ""),
      bullet("Microsoft Excel workbook for the full KPI table export.", ""),
      bullet("Data source: DataCo Smart Supply Chain Dataset, Kaggle (kagglehub: shashwatwork/dataco-smart-supply-chain-for-big-data-analysis).", ""),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("/sessions/serene-amazing-cori/work/dashboard/Regional_Outbound_Fulfillment_Case_Study.docx", buffer);
  console.log("DOCX written.");
});
