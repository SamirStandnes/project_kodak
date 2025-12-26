import sys
import os

# Add the project root directory to sys.path
# (3 levels up from scripts/debug/check_cash_balance.py)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from scripts.analysis.generate_summary_report import generate_summary_report

try:
    df, summary, unpriced = generate_summary_report(verbose=True)
    print(f"\nCalculated Cash Balance: {summary['current_cash_balance']:,.2f} NOK")
except Exception as e:
    print(f"Error: {e}")

