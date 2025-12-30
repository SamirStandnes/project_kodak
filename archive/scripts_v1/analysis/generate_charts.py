import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

def set_style():
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']

def plot_sector_allocation(df, output_path):
    """
    Generates a pie chart of portfolio allocation by Sector.
    """
    set_style()
    
    # Group by Sector and sum MarketValue_NOK
    sector_data = df.groupby('Sector')['MarketValue_NOK'].sum().sort_values(ascending=False)
    
    # Filter out tiny sectors if too many (optional, but good for readability)
    total_val = sector_data.sum()
    sector_data = sector_data[sector_data / total_val > 0.01] # Keep > 1%
    
    plt.figure(figsize=(10, 6))
    plt.title('Portfolio Allocation by Sector', fontsize=16, pad=20)
    
    # Create pie chart
    wedges, texts, autotexts = plt.pie(
        sector_data, 
        labels=sector_data.index, 
        autopct='%1.1f%%',
        startangle=140,
        pctdistance=0.85,
        explode=[0.05] * len(sector_data) # Slight explosion for all
    )
    
    # Draw circle for Donut Chart style
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    
    plt.setp(autotexts, size=9, weight="bold")
    plt.setp(texts, size=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved sector chart to {output_path}")

def plot_yearly_returns(yearly_data, output_path):
    """
    Generates a bar chart of Yearly XIRR Returns.
    """
    set_style()
    
    if not yearly_data:
        print("No yearly data to plot.")
        return

    df = pd.DataFrame(yearly_data)
    # Convert decimal to percentage for plotting
    df['Return_Pct'] = df['Return'] * 100
    
    plt.figure(figsize=(10, 6))
    
    # Color bars: Green for positive, Red for negative
    colors = ['#2ecc71' if x >= 0 else '#e74c3c' for x in df['Return_Pct']]
    
    ax = sns.barplot(x='Year', y='Return_Pct', data=df, palette=colors, hue='Year', legend=False)
    
    plt.title('Yearly Portfolio Performance (XIRR)', fontsize=16, pad=20)
    plt.ylabel('Annual Return (%)', fontsize=12)
    plt.xlabel('Year', fontsize=12)
    
    # Add value labels on bars
    for i, v in enumerate(df['Return_Pct']):
        ax.text(i, v + (1 if v > 0 else -2), f"{v:.1f}%", ha='center', fontweight='bold')
    
    plt.axhline(0, color='black', linewidth=1) # Zero line
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved yearly returns chart to {output_path}")
