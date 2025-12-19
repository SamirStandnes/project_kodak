import sys
import os
from datetime import datetime
from fpdf import FPDF

# Add project root to the Python path to allow importing from other script directories
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from scripts.analysis.generate_summary_report import generate_summary_report

class ReportPDF(FPDF):
    def header(self):
        # Set font for the header
        self.set_font('Helvetica', 'B', 12)
        # Title
        self.cell(0, 10, 'Portfolio Summary Report', 0, 1, 'C')
        # Line break
        self.ln(10)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Set font for the footer
        self.set_font('Helvetica', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def title_page(self):
        self.add_page()
        self.set_font('Helvetica', 'B', 24)
        self.cell(0, 80, 'Portfolio Performance Report', 0, 1, 'C')
        self.set_font('Helvetica', '', 16)
        self.cell(0, 10, f"As of {datetime.now().strftime('%B %d, %Y')}", 0, 1, 'C')

    def holdings_table(self, df):
        self.add_page(orientation='L') # Landscape for wide table
        self.set_font('Helvetica', 'B', 10)
        
        # Column Headers
        headers = ['Symbol', 'Qty', 'Weight', 'Avg. Cost', 'FIFO Cost', 'Latest Price', 'Market Value', 'Return (Avg)', 'Return (FIFO)']
        col_widths = [35, 20, 20, 25, 25, 25, 35, 30, 30]

        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, header, 1, 0, 'C')
        self.ln()

        # Table Body
        self.set_font('Helvetica', '', 9)
        for _, row in df.iterrows():
            self.cell(col_widths[0], 10, str(row["Symbol"]), 1)
            self.cell(col_widths[1], 10, f"{row['Quantity']:,.0f}", 1, 0, 'R')
            self.cell(col_widths[2], 10, f"{row['Weight']:.2%}", 1, 0, 'R')
            self.cell(col_widths[3], 10, f"{row['AvgWAC_NOK']:,.2f}", 1, 0, 'R')
            self.cell(col_widths[4], 10, f"{row['FIFOWAC_NOK']:,.2f}", 1, 0, 'R')
            self.cell(col_widths[5], 10, f"{row['LatestPrice_NOK']:,.2f}", 1, 0, 'R')
            self.cell(col_widths[6], 10, f"{row['MarketValue_NOK']:,.0f}", 1, 0, 'R')
            self.cell(col_widths[7], 10, f"{row['AvgReturn_pct']:.2f}%", 1, 0, 'R')
            self.cell(col_widths[8], 10, f"{row['FIFOReturn_pct']:.2f}%", 1, 0, 'R')
            self.ln()

    def summary_section(self, summary_data):
        self.add_page(orientation='P') # Portrait for summary
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 15, 'Overall Portfolio Summary', 0, 1, 'L')
        self.ln(5)

        self.set_font('Helvetica', '', 12)
        # Define summary items and their formatting
        summary_items = [
            ("Total Market Value", f"{summary_data['total_market_value']:,.0f} NOK"),
            ("Total Gain/Loss (Avg. Cost)", f"{summary_data['total_avg_gain_loss']:,.0f} NOK"),
            ("Total Return (Avg. Cost)", f"{summary_data['total_avg_return_pct']:.2f}%"),
            ("Total Gain/Loss (FIFO)", f"{summary_data['total_fifo_gain_loss']:,.0f} NOK"),
            ("Total Return (FIFO)", f"{summary_data['total_fifo_return_pct']:.2f}%"),
            ("---", "---"),
            ("Total Dividends Received", f"{summary_data['total_dividends']:,.0f} NOK"),
            ("Total Fees Paid", f"{summary_data['total_fees']:,.0f} NOK"),
            ("Total Interest Paid", f"{summary_data['total_interest_paid']:,.0f} NOK"),
            ("---", "---"),
            ("CAGR (XIRR)", f"{summary_data['cagr_xirr']:.2%}"),
        ]
        
        for label, value in summary_items:
            if label == "---":
                self.ln(5)
                continue
            self.set_font('Helvetica', 'B', 12)
            self.cell(90, 10, label, 0, 0, 'L')
            self.set_font('Helvetica', '', 12)
            self.cell(0, 10, value, 0, 1, 'R')

        # --- Last Trade Dates by Source ---
        if summary_data['last_trade_dates_by_source']:
            self.ln(10) # Add some space
            self.set_font('Helvetica', 'B', 14)
            self.cell(0, 10, 'Last Transaction Dates by Source', 0, 1, 'L')
            self.set_font('Helvetica', '', 11)
            for source, date_str in summary_data['last_trade_dates_by_source'].items():
                self.cell(60, 8, f"{source}:", 0, 0, 'L')
                self.cell(0, 8, date_str, 0, 1, 'L')

    def notes_section(self):
        self.add_page(orientation='P')
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 15, 'Notes on Measurement', 0, 1, 'L')
        self.ln(5)

        self.set_font('Helvetica', '', 10)
        notes_text = """
        This report utilizes several key metrics to provide a comprehensive view of portfolio performance. The methodologies are described below.

        Weighted Average Cost (Avg. WAC):
        This is the average cost per share of a security. It is calculated by dividing the total cost of all 'buy' and 'transfer_in' transactions by the total number of shares acquired from those transactions. This method provides a simple average cost over the life of the holding.

        FIFO Cost (First-In, First-Out):
        This method assumes that the first shares purchased are the first shares sold. The cost basis of remaining shares is therefore based on the cost of the most recently purchased shares. This can provide a different view of gains, especially for securities bought at various price points over time.

        Market Value:
        The market value of a holding is calculated by multiplying the number of shares currently held by the last available closing price for that security, converted to the portfolio's base currency (NOK).

        Return %:
        This is the percentage gain or loss for a holding, calculated as: (Market Value / Cost Basis) - 1. It is calculated independently for both the Average Cost and FIFO Cost bases.

        CAGR (XIRR):
        The Compound Annual Growth Rate is a measure of an investment's annual growth rate over time. This report uses the XIRR (Extended Internal Rate of Return) function, which accounts for the specific timing and amount of all cash flows (deposits and withdrawals) into and out of the portfolio, as well as the final market value. It provides the most accurate measure of overall portfolio performance.
        """
        self.multi_cell(0, 5, notes_text)

def main():
    """
    Generates the full PDF report.
    """
    print("Fetching portfolio data...")
    main_df, summary, unpriced = generate_summary_report()
    
    if main_df.empty:
        print("Report generation failed: No data returned from summary report.")
        return

    print("Generating PDF report...")
    pdf = ReportPDF()
    pdf.title_page()
    pdf.holdings_table(main_df)
    pdf.summary_section(summary)
    pdf.notes_section()
    
    output_filename = 'Portfolio_Summary_Report.pdf'
    pdf.output(output_filename)
    
    print(f"Successfully generated {output_filename}")
    if unpriced:
        print("\nWarning: The following securities could not be priced and were excluded from the report tables:")
        for item in unpriced:
            print(f"- {item}")

if __name__ == '__main__':
    main()
