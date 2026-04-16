"""CLI runner for signal backtest report generation."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path
import json
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import matplotlib.pyplot as plt

from src.backtest.signal_backtest import BacktestResult, SignalBacktester


def _equity_chart_base64(result: BacktestResult) -> str:
    fig, ax = plt.subplots(figsize=(10, 4))

    rl_x = [p["date"] for p in result.rl_weighted.get("equity_curve", [])]
    rl_y = [p["cumulative_pnl"] for p in result.rl_weighted.get("equity_curve", [])]
    eq_x = [p["date"] for p in result.equal_weight.get("equity_curve", [])]
    eq_y = [p["cumulative_pnl"] for p in result.equal_weight.get("equity_curve", [])]

    ax.plot(rl_x, rl_y, label="RL Weighted", color="#1f77b4")
    ax.plot(eq_x, eq_y, label="Equal Weight", color="#ff7f0e")
    ax.set_title("Equity Curve")
    ax.set_ylabel("Cumulative P&L (INR)")
    ax.tick_params(axis="x", labelrotation=45)
    ax.legend()
    fig.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=140)
    plt.close(fig)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _agent_rows(result: BacktestResult) -> str:
    agents = result.rl_weighted.get("per_agent_accuracy", [])
    if not agents:
        return "<tr><td colspan='4'>No agent signal history available.</td></tr>"

    parts = []
    for row in agents:
        parts.append(
            "<tr>"
            f"<td>{row['agent_name']}</td>"
            f"<td>{row['correct']}</td>"
            f"<td>{row['total']}</td>"
            f"<td>{row['accuracy']:.4f}</td>"
            "</tr>"
        )
    return "".join(parts)


def _summary_row(name: str, metrics: dict) -> str:
    return (
        "<tr>"
        f"<td>{name}</td>"
        f"<td>{metrics.get('win_rate', 0.0):.4f}</td>"
        f"<td>{metrics.get('total_pnl', 0.0):.2f}</td>"
        f"<td>{metrics.get('sharpe_ratio', 0.0):.4f}</td>"
        f"<td>{metrics.get('max_drawdown', 0.0):.2f}</td>"
        "</tr>"
    )


def _html_report(result: BacktestResult) -> str:
    chart = _equity_chart_base64(result)
    payload = json.dumps(SignalBacktester.to_dict(result))

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>RITAM Signal Backtest</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
h1 {{ margin-bottom: 0; }}
.sub {{ color: #6b7280; margin-top: 4px; }}
table {{ border-collapse: collapse; width: 100%; margin: 14px 0; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
th {{ background: #f3f4f6; }}
.card {{ border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin-top: 16px; }}
code {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>RITAM Signal Backtest</h1>
<p class="sub">Range: {result.from_date} → {result.to_date} | Generated: {result.generated_at}</p>

<div class="card">
<h2>Summary</h2>
<table>
<thead><tr><th>Strategy</th><th>Win Rate</th><th>Total P&amp;L (INR)</th><th>Sharpe</th><th>Max Drawdown (INR)</th></tr></thead>
<tbody>
{_summary_row('RL Weighted', result.rl_weighted)}
{_summary_row('Equal Weight', result.equal_weight)}
</tbody>
</table>
</div>

<div class="card">
<h2>Equity Curve</h2>
<img alt="equity curve" style="max-width: 100%;" src="data:image/png;base64,{chart}" />
</div>

<div class="card">
<h2>Per-Agent Accuracy</h2>
<table>
<thead><tr><th>Agent</th><th>Correct</th><th>Total</th><th>Accuracy</th></tr></thead>
<tbody>
{_agent_rows(result)}
</tbody>
</table>
</div>

<script id="backtest-result" type="application/json">{payload}</script>
</body>
</html>
""".strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RITAM signal backtest")
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--walk-forward", action="store_true", default=False)
    args = parser.parse_args()

    result = SignalBacktester().run(
        from_date=args.from_date,
        to_date=args.to_date,
        walk_forward=args.walk_forward,
    )

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_name = f"backtest_{datetime.utcnow().date().isoformat()}.html"
    report_path = reports_dir / report_name
    report_path.write_text(_html_report(result), encoding="utf-8")

    print(f"Report saved: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
