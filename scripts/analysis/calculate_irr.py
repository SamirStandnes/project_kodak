
import pandas as pd
import numpy as np # numpy is often needed for numerical operations
from scipy.optimize import newton # For XIRR calculation
import os

INPUT_FILE_PATH = os.path.join('data', 'processed_cash_flows.csv')
IRR_CASH_FLOWS_OUTPUT_FILE = os.path.join('data', 'irr_cash_flows.csv')

# --- Custom XIRR Implementation ---
def xirr_custom(cash_flows, dates):
    """
    Calculate XIRR for irregular cash flows using Newton's method.
    cash_flows: A list/array of cash flows (positive for inflows, negative for outflows).
    dates: A list/array of dates corresponding to the cash flows.
    """
    # Ensure dates are datetime objects and sorted
    dates = pd.to_datetime(dates)
    if not all(dates == dates.sort_values()):
        raise ValueError("Dates must be sorted.")

    # Convert dates to number of days from the first date - REMOVE .dt
    day_counts = (dates - dates.min()).days # Corrected line

    def npv_function(rate):
        # Calculate NPV for a given rate
        # Ensure that (1 + rate) is not zero or negative for fractional powers
        # For XIRR, rate is typically expected to be > -1
        # If rate is very small negative, (1+rate)**(days/365) could become very large positive or negative
        # which can cause issues. Add a check or limit the rate.
        if rate <= -1.0: # Rates less than -100% are usually not economically meaningful for this
            return np.inf if sum(c for c in cash_flows if c < 0) < 0 else -np.inf # Diverge if rate too low
        return sum(cf / (1 + rate)**(days / 365.0) for cf, days in zip(cash_flows, day_counts))

    # Initial guess for the rate (often 0.1 or 0.0)
    # Handle cases where all cash flows are negative or positive
    if all(cf >= 0 for cf in cash_flows):
        return np.nan # Cannot calculate XIRR if all cash flows are positive (or zero)
    if all(cf <= 0 for cf in cash_flows):
        return np.nan # Cannot calculate XIRR if all cash flows are negative (or zero)

    try:
        # Use Newton's method to find the root of the NPV function
        # The initial guess can be important.
        return newton(npv_function, 0.1, tol=1e-6, maxiter=100) # Initial guess 10%
    except RuntimeError:
        # newton might fail to converge
        return np.nan
    except ZeroDivisionError:
        # Happens if (1 + rate) becomes 0 or negative during iteration.
        return np.nan
    except Exception as e:
        print(f"An unexpected error occurred during XIRR calculation: {e}")
        return np.nan

def calculate_portfolio_irr(df):
    # Filter for Capital In and Capital Out transactions
    irr_df = df[df['CashFlowCategory'].isin(['Capital_In', 'Capital_Out'])].copy()

    # Sort by TradeDate
    irr_df = irr_df.sort_values(by='TradeDate')

    # Group by TradeDate and sum Amount_NOK for each date
    grouped_cash_flows = irr_df.groupby('TradeDate')['Amount_NOK'].sum().reset_index()

    # Ensure cash flows are numeric and handle any NaNs
    grouped_cash_flows['Amount_NOK'] = pd.to_numeric(grouped_cash_flows['Amount_NOK'], errors='coerce').fillna(0)

    # Extract values and dates for XIRR calculation
    dates = grouped_cash_flows['TradeDate'] # Keep as Series for custom xirr
    amounts = grouped_cash_flows['Amount_NOK'].astype(float) # Ensure float

    if len(amounts) < 2:
        print("Not enough cash flows to calculate XIRR (need at least two).")
        return None, grouped_cash_flows
    if amounts.sum() == 0:
        print("Sum of cash flows is zero, XIRR cannot be calculated.")
        return None, grouped_cash_flows
    # The new xirr_custom handles the positive/negative check.

    try:
        irr_value = xirr_custom(amounts.values, dates.values) # Pass numpy arrays
        return irr_value, grouped_cash_flows
    except Exception as e:
        print(f"Error calculating XIRR with custom function: {e}")
        return None, grouped_cash_flows


# --- Main Execution ---
if __name__ == "__main__":
    print(f"Loading processed cash flows from {INPUT_FILE_PATH}...")
    try:
        # Ensure TradeDate is parsed as datetime
        processed_df = pd.read_csv(INPUT_FILE_PATH, parse_dates=['TradeDate'])

        irr_value, cash_flows_used = calculate_portfolio_irr(processed_df.copy())

        if irr_value is not None and not np.isnan(irr_value):
            print(f"\nCalculated Annualized Internal Rate of Return (XIRR): {irr_value:.4f} ({irr_value * 100:.2f}%)")
        else:
            print("\nCould not calculate XIRR. Please check the cash flow data for sufficient inflows/outflows or if the NPV function has a root.")

        # Save the cash flows used for IRR calculation
        if cash_flows_used is not None and not cash_flows_used.empty:
            cash_flows_used.to_csv(IRR_CASH_FLOWS_OUTPUT_FILE, index=False, encoding='utf-8')
            print(f"Cash flows used for XIRR calculation saved to {IRR_CASH_FLOWS_OUTPUT_FILE}")
        
    except FileNotFoundError:
        print(f"Error: Processed cash flows file not found at {INPUT_FILE_PATH}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
