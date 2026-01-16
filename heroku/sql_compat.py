"""
SQLite to PostgreSQL query translation layer.
Translates SQLite-specific SQL syntax to PostgreSQL equivalents.
"""
import re


def translate_query(query: str) -> str:
    """
    Translates SQLite-specific SQL to PostgreSQL.

    Handles:
    - strftime('%Y', date) -> TO_CHAR(date::date, 'YYYY')
    - strftime('%J', date) -> EXTRACT(DOY FROM date::date)
    - date('now', '-12 months') -> CURRENT_DATE - INTERVAL '12 months'
    - INSERT OR REPLACE -> INSERT ... ON CONFLICT DO UPDATE
    - ? placeholders -> %s placeholders
    - sqlite_master -> pg_tables
    """
    result = query

    # strftime('%Y', column) -> TO_CHAR(column::date, 'YYYY')
    # Matches: strftime('%Y', date) or strftime('%Y', t.date)
    result = re.sub(
        r"strftime\s*\(\s*'%Y'\s*,\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\)",
        r"TO_CHAR(\1::date, 'YYYY')",
        result
    )

    # strftime('%J', column) for Julian day -> EXTRACT(DOY FROM column::date)
    # Used for finding closest date: ABS(strftime('%J', t.date) - strftime('%J', ?))
    # PostgreSQL: ABS(EXTRACT(DOY FROM t.date::date) - EXTRACT(DOY FROM %s::date))
    result = re.sub(
        r"strftime\s*\(\s*'%J'\s*,\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\)",
        r"EXTRACT(DOY FROM \1::date)",
        result
    )

    # strftime('%J', ?) -> EXTRACT(DOY FROM %s::date)
    # Handle the parameter placeholder version
    result = re.sub(
        r"strftime\s*\(\s*'%J'\s*,\s*\?\s*\)",
        r"EXTRACT(DOY FROM %s::date)",
        result
    )

    # date('now', '-12 months') -> CURRENT_DATE - INTERVAL '12 months'
    result = re.sub(
        r"date\s*\(\s*'now'\s*,\s*'-(\d+)\s+months?'\s*\)",
        r"CURRENT_DATE - INTERVAL '\1 months'",
        result
    )

    # INSERT OR REPLACE INTO table (...) VALUES (...)
    # -> INSERT INTO table (...) VALUES (...) ON CONFLICT DO UPDATE SET ...
    # This is complex because we need to know the conflict target
    # For market_prices: conflict on (instrument_id, date)
    # For exchange_rates: conflict on (from_currency, to_currency, date)
    result = translate_insert_or_replace(result)

    # sqlite_master -> pg_tables (for system table queries)
    result = result.replace("sqlite_master WHERE type='table'",
                           "pg_tables WHERE schemaname='public'")
    result = result.replace("name FROM pg_tables", "tablename as name FROM pg_tables")

    # Replace ? placeholders with %s for psycopg2
    # But be careful not to replace ? inside strings
    result = replace_placeholders(result)

    return result


def translate_insert_or_replace(query: str) -> str:
    """
    Translates INSERT OR REPLACE to PostgreSQL ON CONFLICT syntax.

    Market prices table: conflict on (instrument_id, date)
    Exchange rates table: conflict on (from_currency, to_currency, date)
    """
    # Pattern for INSERT OR REPLACE INTO market_prices
    market_prices_pattern = re.compile(
        r"INSERT\s+OR\s+REPLACE\s+INTO\s+market_prices\s*\(\s*"
        r"([^)]+)\s*\)\s*VALUES\s*\(\s*([^)]+)\s*\)",
        re.IGNORECASE
    )

    match = market_prices_pattern.search(query)
    if match:
        columns = match.group(1)
        values = match.group(2)
        return f"""INSERT INTO market_prices ({columns})
VALUES ({values})
ON CONFLICT (instrument_id, date) DO UPDATE SET
    close = EXCLUDED.close,
    currency = EXCLUDED.currency,
    source = EXCLUDED.source"""

    # Pattern for INSERT OR REPLACE INTO exchange_rates
    exchange_rates_pattern = re.compile(
        r"INSERT\s+OR\s+REPLACE\s+INTO\s+exchange_rates\s*\(\s*"
        r"([^)]+)\s*\)\s*VALUES\s*\(\s*([^)]+)\s*\)",
        re.IGNORECASE
    )

    match = exchange_rates_pattern.search(query)
    if match:
        columns = match.group(1)
        values = match.group(2)
        return f"""INSERT INTO exchange_rates ({columns})
VALUES ({values})
ON CONFLICT (from_currency, to_currency, date) DO UPDATE SET
    rate = EXCLUDED.rate"""

    return query


def replace_placeholders(query: str) -> str:
    """
    Replaces SQLite ? placeholders with PostgreSQL %s placeholders.
    Carefully avoids replacing ? inside string literals.
    """
    result = []
    in_string = False
    string_char = None

    i = 0
    while i < len(query):
        char = query[i]

        # Track string literals
        if char in ("'", '"') and (i == 0 or query[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
                string_char = None

        # Replace ? with %s if not in a string
        if char == '?' and not in_string:
            result.append('%s')
        else:
            result.append(char)

        i += 1

    return ''.join(result)
