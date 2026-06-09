# snow-finance-analytics

A working demo of an AI-first Finance Analytics workflow — built the way the
Snowflake Finance Analytics team describes its stack: **a reusable skill
(YAML + Markdown), a Streamlit app, a Cortex Analyst-style semantic model,
window-function SQL, and a formatted multi-tab Excel earnings pack.**

Built end-to-end with an AI coding assistant (Claude) as the primary
development tool, on Snowflake's own publicly reported financials
(8-K filings, FY25 through Q1 FY27).

## What's in here

```
snow-finance-analytics/
├── app.py                          # Streamlit revenue analytics app
├── data/snow_quarterly_metrics.csv # SNOW quarterly metrics (8-K sourced)
├── skills/quarterly-revenue-analysis/
│   ├── skill.yaml                  # Structured skill: triggers, inputs, steps, quality gates
│   └── SKILL.md                    # Domain instructions, audience templates, edge cases
├── semantic/finance_semantic_model.yaml  # Cortex Analyst-style semantic model
├── sql/revenue_analysis.sql        # CTEs + window functions: growth, bridges, trend flags
└── exports/build_earnings_pack.py  # openpyxl multi-tab formatted Excel export
```

## Run it

```bash
pip install -r requirements.txt

# Streamlit app
streamlit run app.py

# Earnings pack (multi-tab Excel)
python exports/build_earnings_pack.py --quarter "Q1 FY27"
```

## Design notes

- **Skill-first.** The analysis logic lives in `skills/quarterly-revenue-analysis/`,
  not in anyone's head. A non-technical analyst invokes it with one prompt
  ("run the Q1 FY27 revenue review for senior leadership") and gets
  audience-appropriate output with hard quality gates: every figure must
  reconcile to the source table; growth rates are recomputed, never quoted.
- **Same code, local or deployed.** `app.py` reads the bundled CSV locally;
  point `load_metrics()` at `FINANCE.REPORTING.QUARTERLY_METRICS` via Snowpark
  and it deploys as a Streamlit-in-Snowflake app unchanged.
- **Semantic layer.** `finance_semantic_model.yaml` encodes the gotchas a
  text-to-SQL model needs: fiscal year ends Jan 31, NRR/RPO are point-in-time
  (never summed), "growth" defaults to YoY on product revenue. Includes
  verified queries.
- **IR-safe by construction.** The skill's `investor_relations` audience mode
  only emits externally disclosed metrics and refuses to interpolate.

## Data sources

Quarterly figures compiled from Snowflake's 8-K earnings releases
([sec.gov](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001640147&type=8-K)).
Headline metrics (product revenue, NRR, RPO) are as reported; a few
non-headline fields (e.g., total revenue for recent quarters) are estimates
where not separately disclosed, flagged for a demo context.

---

*Regis Yizerwe — yizerwer@gmail.com*
