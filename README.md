# Business Opportunity Lab — MIS3012 Group 14

A four-screen Streamlit implementation of Report 1. All prices, supplier offers and bundled review examples are assumed/synthetic, not observed marketplace evidence. This is a local prototype; do not treat simulated sales as a forecast.

## Run (macOS / Windows)

Install Python 3.10 or later. Open a terminal in this extracted folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

On Windows, use `py -m venv .venv` and `.venv\Scripts\activate` instead, then `python -m pip install -r requirements.txt` and `python -m streamlit run app.py`. Open the localhost URL printed by Streamlit. No API key is needed for the offline keyword preview. Optional LLM analysis uses an OpenAI-compatible endpoint (for example a provider's compatible API) configured in the sidebar. The review text is sent to that provider only when AI analysis is clicked; never upload reviews without permission.

## Demo path

1. Setup: keep $500 budget, $100 inventory limit and $150 protected cash. The included ten reviews are synthetic software-test examples. Edit the three offers in their expanders. Product B uses the exact report example.
2. Compare: inspect source excerpts and compare A, B, C; choose B. Offline analysis is keyword-based, not AI. The optional LLM returns theme summaries and review IDs; quotations are retrieved verbatim from the input. Manually review summaries for correctness.
3. Check costs: B yields $13.90 contribution, $90 inventory, $390 required cash, 6 break-even sales, 8 cash-recovery sales and $59 profit at ten sales. Try fewer units sold.
4. Decide: B should be RESEARCH FURTHER by default because evidence and quote are not verified. Change B's MOQ to 100 (quantity 10 fails MOQ; change quantity to 100 to also see budget violations). For the report's second scenario change setup to $100 and advertising to $120; ten sales yields -$81 and 100 units requires $1,970 (the report states $1,830, inconsistent with its own formula: $900 + $700 + $220 + $150 = $1,970). Real small-test recommendations are gated by positive economics, seller limits, verified quote/fit, observed review evidence, real demand reference and confirmation. These are user attestations, not independent verification.
5. Run the synthetic joint market or separate matched focal markets. Save a decision; changes create a new SQLite record. Export decision records and simulation logs from the Decide screen.

## Standalone simulator

```bash
python3 simulator.py --seed 1401 --output simulation_output
python3 simulator.py --seed 1401 --focal B --output focal_B
python3 -m unittest -v
```

`--input data/market.json` accepts a fixed JSON configuration. The simulator creates 100 buyers in the report's 30/30/20/20 segments, uses exactly 100 trading rounds and a fixed seed, models delayed payments, and writes inputs, buyer profiles, transaction logs, per-round cash/stock/profit and summary results. Joint runs include three competing sellers; focal runs reuse matched buyer conditions. The preference model and some non-B cost assumptions are new illustrative implementation choices, so the outputs are not asserted to reproduce the earlier report's 42/10/13 sales. The experiment can intentionally examine financially infeasible offers; the app will still block a real test. No actual purchasing function exists.

## Files
- `app.py` four screens and UI state; `finance.py` deterministic formulas and guardrails.
- `reviews.py` parser, duplicate removal, keyword fallback and optional AI analysis with traceable excerpts.
- `simulator.py` independent market experiment; `storage.py` SQLite decision history (local single-user prototype).
- `data/market.json`, `data/reviews.csv` labeled demonstration inputs; `test_core.py` unit tests.

## Remaining course work
Collect permitted review data, real comparable listings and quotes, label observed/assumed/synthetic inputs, validate LLM results against human labels and conduct the planned baseline and 6–8 participant usability evaluation. The prototype does not claim these evaluations have been completed. For a public multi-user deployment, add authentication and isolated persistent storage; local SQLite is intended for single-user demos.
