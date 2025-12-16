import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import configparser
import pandas as pd
from datetime import datetime

# Add project root to the Python path to allow importing from other script directories
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Import the refactored report generator
from scripts.analysis.generate_summary_report import generate_summary_report

def load_config():
    """Loads SMTP and recipient configuration from config.ini."""
    config = configparser.ConfigParser()
    config_path = os.path.join(project_root, 'config.ini')
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at '{config_path}'.", file=sys.stderr)
        print("Please copy 'config.ini.example' to 'config.ini' and fill in your details.", file=sys.stderr)
        sys.exit(1)
    config.read(config_path)
    try:
        smtp_config = {
            "server": config.get('SMTP', 'SERVER'),
            "port": config.getint('SMTP', 'PORT'),
            "user": config.get('SMTP', 'USER'),
            "password": config.get('SMTP', 'PASSWORD')
        }
        recipient_email = config.get('RECIPIENT', 'EMAIL')
        return smtp_config, recipient_email
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"Error: Missing configuration in 'config.ini': {e}", file=sys.stderr)
        sys.exit(1)

def create_html_body(df, summary_data, unpriced):
    """Creates a styled HTML string from the portfolio data."""

    # --- CSS Styling ---
    html_style = """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            margin: 20px;
            color: #333;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .portfolio-table {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .portfolio-table th {
            border-bottom: 2px solid #34495e;
            padding: 12px;
            text-align: left;
            background-color: #ecf0f1;
            color: #2c3e50;
        }
        .portfolio-table td {
            border-bottom: 1px solid #ddd;
            padding: 10px;
        }
        .portfolio-table tbody tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .summary-table {
            width: 50%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .summary-table td {
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
        .summary-table td:first-child {
            font-weight: bold;
            color: #555;
        }
        .positive {
            color: #27ae60;
        }
        .negative {
            color: #c0392b;
        }
        .unpriced-list {
            list-style-type: none;
            padding: 0;
        }
        .unpriced-list li {
            color: #e67e22;
        }
        .footer {
            margin-top: 30px;
            font-size: 12px;
            color: #95a5a6;
        }
    </style>
    """

    # --- Data Formatting ---
    df_html = df.copy()
    
    # Define columns to format
    money_cols = ['AvgWAC_NOK', 'FIFOWAC_NOK', 'MarketValue_NOK']
    pct_cols = ['AvgReturn_pct', 'FIFOReturn_pct']
    
    for col in money_cols:
        df_html[col] = df_html[col].map('{:,.0f}'.format)
    
    for col in pct_cols:
        df_html[col] = df_html[col].apply(lambda x: f'<span class="{"positive" if x >= 0 else "negative"}">{x:.2f}%</span>')

    df_html.rename(columns={
        "Symbol": "Symbol", 
        "Quantity": "Quantity", 
        "AvgWAC_NOK": "Avg. Cost", 
        "FIFOWAC_NOK": "FIFO Cost", 
        "MarketValue_NOK": "Market Value (NOK)", 
        "AvgReturn_pct": "Return % (Avg)", 
        "FIFOReturn_pct": "Return % (FIFO)"
    }, inplace=True)
    
    # Keep only relevant columns for display
    display_cols = ["Symbol", "Quantity", "Avg. Cost", "FIFO Cost", "Market Value (NOK)", "Return % (Avg)", "Return % (FIFO)"]
    
    # --- HTML Structure ---
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Portfolio Summary</title>
        {html_style}
    </head>
    <body>
        <h1>Portfolio Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Positions</h2>
        {df_html[display_cols].to_html(index=False, border=0, classes='portfolio-table', escape=False)}
        
        <h2>Summary (NOK)</h2>
        <table class="summary-table">
            <tr><td>Total Market Value</td><td>{summary_data['total_market_value']:,.0f}</td></tr>
            <tr><td>Total Gain/Loss (Economic)</td><td class="{'positive' if summary_data['total_avg_gain_loss'] >= 0 else 'negative'}">{summary_data['total_avg_gain_loss']:,.0f}</td></tr>
            <tr><td>Total Return (Economic)</td><td class="{'positive' if summary_data['total_avg_return_pct'] >= 0 else 'negative'}">{summary_data['total_avg_return_pct']:.2f}%</td></tr>
            <tr><td>Total Gain/Loss (FIFO)</td><td class="{'positive' if summary_data['total_fifo_gain_loss'] >= 0 else 'negative'}">{summary_data['total_fifo_gain_loss']:,.0f}</td></tr>
            <tr><td>Total Return (FIFO)</td><td class="{'positive' if summary_data['total_fifo_return_pct'] >= 0 else 'negative'}">{summary_data['total_fifo_return_pct']:.2f}%</td></tr>
            <tr><td>Total Dividends</td><td>{summary_data['total_dividends']:,.0f}</td></tr>
            <tr><td>Total Fees</td><td>{summary_data['total_fees']:,.0f}</td></tr>
            <tr><td>Total Interest Paid</td><td>{summary_data['total_interest_paid']:,.0f}</td></tr>
        </table>
    """

    if unpriced:
        html += "<h3>Securities Without Price</h3><ul class='unpriced-list'>"
        for item in unpriced:
            html += f"<li>{item}</li>"
        html += "</ul>"
        
    html += '<p class="footer">This is an automatically generated report.</p></body></html>'
    
    return html

def send_email(subject, html_body, to_addr, smtp_config):
    """Sends an email using the configured SMTP settings."""
    print(f"Preparing to send HTML email to {to_addr}...")
    
    msg = MIMEMultipart()
    msg['From'] = smtp_config["user"]
    msg['To'] = to_addr
    msg['Subject'] = subject
    
    # Attach the HTML body
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        with smtplib.SMTP(smtp_config["server"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
            server.send_message(msg)
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error: Failed to send email. {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Main function to load config, generate the report, and send the email."""
    # 1. Load configuration
    smtp_config, recipient_email = load_config()
    
    # 2. Generate the report data
    print("Generating portfolio report data...")
    main_df, summary, unpriced = generate_summary_report(verbose=False)
    
    if main_df.empty:
        print("No portfolio data to generate a report.")
        return

    # 3. Create the HTML body
    print("Creating HTML email body...")
    subject = f"Porteføljerapport - {summary['total_market_value']:,.0f} NOK"
    html_body = create_html_body(main_df, summary, unpriced)
    
    # 4. Send the email
    send_email(subject, html_body, recipient_email, smtp_config)

if __name__ == "__main__":
    main()