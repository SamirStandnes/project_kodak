import sqlite3
import pandas as pd

def show_wac_by_account():
    """
    Queries the database and displays the Weighted Average Cost (WAC) 
    for each security, grouped by account.
    """
    db_file = 'database/portfolio.db'
    conn = sqlite3.connect(db_file)
    
    query = '''
        SELECT
            T.AccountID,
            ISM.Symbol,
            WAC.ISIN,
            WAC.WeightedAverageCost
        FROM
            weighted_average_costs WAC
        JOIN
            isin_symbol_map ISM ON WAC.ISIN = ISM.ISIN
        JOIN
            transactions T ON WAC.ISIN = T.ISIN
        GROUP BY
            T.AccountID, WAC.ISIN
        ORDER BY
            T.AccountID, ISM.Symbol
    '''
    
    try:
        df = pd.read_sql_query(query, conn)
        
        print('--- Weighted Average Cost (WAC) per Security per Account ---')
        
        if df.empty:
            print("No data to display.")
        else:
            for account in df['AccountID'].unique():
                print(f'\n--- Account: {account} ---')
                account_df = df[df['AccountID'] == account]
                print(account_df[['Symbol', 'ISIN', 'WeightedAverageCost']].to_string(index=False))

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    show_wac_by_account()
