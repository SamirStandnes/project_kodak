import sys
import os
from datetime import datetime
from fpdf import FPDF

# Add project root to the Python path to allow importing from other script directories
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from scripts.analysis.generate_summary_report import generate_summary_report
from scripts.analysis.calculate_yearly_returns import calculate_yearly_returns
from scripts.analysis.generate_charts import plot_sector_allocation, plot_yearly_returns

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
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'Current Portfolio Holdings', 0, 1, 'L')
        self.ln(5)
        
        self.set_font('Helvetica', 'B', 10)
        
        # Column Headers
        headers = ['Symbol', 'Sector', 'Qty', 'Weight', 'Avg. Cost', 'FIFO Cost', 'Latest Price', 'Market Value', 'Return (Avg)']
        col_widths = [25, 35, 20, 18, 25, 25, 25, 30, 25]

        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, header, 1, 0, 'C')
        self.ln()

        # Table Body
        self.set_font('Helvetica', '', 9)
        for _, row in df.iterrows():
            self.cell(col_widths[0], 10, str(row["Symbol"]), 1)
            self.cell(col_widths[1], 10, str(row.get("Sector", "N/A"))[:18], 1)
            self.cell(col_widths[2], 10, f"{row['Quantity']:,.0f}", 1, 0, 'R')
            self.cell(col_widths[3], 10, f"{row['Weight']:.2%}", 1, 0, 'R')
            self.cell(col_widths[4], 10, f"{row['AvgWAC_NOK']:,.2f}", 1, 0, 'R')
            self.cell(col_widths[5], 10, f"{row['FIFOWAC_NOK']:,.2f}", 1, 0, 'R')
            self.cell(col_widths[6], 10, f"{row['LatestPrice_NOK']:,.2f}", 1, 0, 'R')
            self.cell(col_widths[7], 10, f"{row['MarketValue_NOK']:,.0f}", 1, 0, 'R')
            
            # Color coding for returns
            avg_ret = row['AvgReturn_pct']
            self.set_text_color(0, 150, 0) if avg_ret >= 0 else self.set_text_color(200, 0, 0)
            self.cell(col_widths[8], 10, f"{avg_ret:.2f}%", 1, 0, 'R')
            self.set_text_color(0, 0, 0) # Reset
            
            self.ln()

    def yearly_performance_section(self, yearly_data, chart_path):
        self.add_page(orientation='P')
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 15, 'Yearly Performance History (XIRR)', 0, 1, 'L')
        self.ln(5)
        
        # Embed Chart
        if os.path.exists(chart_path):
            self.image(chart_path, x=10, y=None, w=190)
            self.ln(5)

        if not yearly_data:
            self.set_font('Helvetica', 'I', 12)
            self.cell(0, 10, "No yearly data available.", 0, 1, 'L')
            return

        self.ln(5)
        
        # Table Header
        self.set_font('Helvetica', 'B', 12)
        self.cell(40, 10, "Year", 1, 0, 'C')
        self.cell(60, 10, "Annual Return", 1, 1, 'C')

        # Table Body
        self.set_font('Helvetica', '', 12)
        for row in yearly_data:
            self.cell(40, 10, str(row['Year']), 1, 0, 'C')
            
            ret = row['Return']
            if ret is not None:
                self.set_text_color(0, 150, 0) if ret >= 0 else self.set_text_color(200, 0, 0)
                self.cell(60, 10, f"{ret:.2%}", 1, 1, 'R')
                self.set_text_color(0, 0, 0)
            else:
                self.cell(60, 10, "N/A", 1, 1, 'C')

    def sector_allocation_section(self, chart_path):
        self.add_page(orientation='P')
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 15, 'Sector Allocation', 0, 1, 'L')
        self.ln(5)
        
        if os.path.exists(chart_path):
            self.image(chart_path, x=10, y=None, w=190)
        else:
             self.cell(0, 10, "Chart not found.", 0, 1)

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
            # Colorize Return % and Gain/Loss
            if "Return" in label or "Gain/Loss" in label or "CAGR" in label:
                try:
                    num_val = float(value.replace(' NOK', '').replace('%', '').replace(',', ''))
                    self.set_text_color(0, 150, 0) if num_val >= 0 else self.set_text_color(200, 0, 0)
                except: pass
            
            self.cell(0, 10, value, 0, 1, 'R')
            self.set_text_color(0, 0, 0)

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

    print("Calculating yearly returns...")
    yearly_returns = calculate_yearly_returns()

    # Generate Charts
    print("Generating charts...")
    chart_dir = os.path.join("reports", "temp_charts")
    if not os.path.exists(chart_dir):
        os.makedirs(chart_dir)
        
    sector_chart_path = os.path.join(chart_dir, "sector_allocation.png")
    yearly_chart_path = os.path.join(chart_dir, "yearly_returns.png")
    
    plot_sector_allocation(main_df, sector_chart_path)
    plot_yearly_returns(yearly_returns, yearly_chart_path)

    print("Generating PDF report...")
    pdf = ReportPDF()
    pdf.title_page()
    pdf.summary_section(summary)
    pdf.sector_allocation_section(sector_chart_path) # New Chart Section
    pdf.yearly_performance_section(yearly_returns, yearly_chart_path) # Enhanced Table + Chart
    pdf.holdings_table(main_df)
    pdf.notes_section()
    
    output_filename = os.path.join('reports', 'Portfolio_Summary_Report.pdf')
    pdf.output(output_filename)
    
    print(f"Successfully generated {output_filename}")
    if unpriced:
        print("\nWarning: The following securities could not be priced and were excluded from the report tables:")
        for item in unpriced:
            print(f"- {item}")

if __name__ == '__main__':
    main()