from datetime import datetime

def parse_date_flexible(date_string):
    """
    Parses a date string that could be in one of several formats.
    Returns a datetime object or None if parsing fails.
    """
    if not date_string:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    return None
