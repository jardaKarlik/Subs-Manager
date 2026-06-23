"""
Wallet API response parser - converts API response to data table format
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


@dataclass
class WalletRecord:
    """Flattened wallet record for data table display"""
    date: str
    type: str
    amount: float
    currency: str
    counterParty: str
    category: str
    category_group: str
    note: str
    recordId: str


def parse_wallet_response(response_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse wallet API response and extract records for data table.

    Args:
        response_data: List containing single dict with API response

    Returns:
        Dict with 'records' (list of dicts), 'summary', and 'pagination' info
    """
    if not response_data or not isinstance(response_data, list):
        return {"records": [], "summary": {}, "pagination": {}}

    api_response = response_data[0]  # API returns array with single object
    records = api_response.get("records", [])

    # Extract pagination info
    pagination = {
        "offset": api_response.get("offset", 0),
        "limit": api_response.get("limit", 200),
        "nextOffset": api_response.get("nextOffset"),
        "hasMore": api_response.get("nextOffset") is not None,
    }

    # Transform records
    flat_records = []
    total_expenses = 0
    total_income = 0

    for record in records:
        flat_record = {
            "date": format_date(record.get("recordDate")),
            "type": determine_type(record.get("amount", {}).get("value", 0)),
            "amount": abs(record.get("amount", {}).get("value", 0)),
            "currency": record.get("amount", {}).get("currencyCode", ""),
            "counterParty": record.get("counterParty", ""),
            "category": record.get("category", {}).get("name", "Uncategorized"),
            "category_group": record.get("category", {}).get("group", {}).get("name", ""),
            "category_color": record.get("category", {}).get("color", "#808080"),
            "note": record.get("note", ""),
            "recordId": record.get("id", ""),
        }
        flat_records.append(flat_record)

        # Calculate totals
        amount = record.get("amount", {}).get("value", 0)
        if amount < 0:
            total_expenses += abs(amount)
        else:
            total_income += amount

    # Sort by date descending
    flat_records.sort(key=lambda x: x["date"], reverse=True)

    summary = {
        "total_records": len(flat_records),
        "total_expenses": round(total_expenses, 2),
        "total_income": round(total_income, 2),
        "net": round(total_income - total_expenses, 2),
        "currency": flat_records[0].get("currency", "") if flat_records else "",
        "period": "Last 3 months",
    }

    return {
        "records": flat_records,
        "summary": summary,
        "pagination": pagination,
    }


def format_date(iso_date: str) -> str:
    """Convert ISO date to readable format"""
    if not iso_date:
        return ""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except:
        return iso_date.split("T")[0] if "T" in iso_date else iso_date


def determine_type(amount: float) -> str:
    """Determine if transaction is expense or income"""
    if amount < 0:
        return "expense"
    elif amount > 0:
        return "income"
    return "transfer"


def to_dataframe(parsed_data: Dict[str, Any]):
    """Convert parsed data to pandas DataFrame (optional)"""
    if not HAS_PANDAS:
        raise ImportError("pandas is required for to_dataframe(). Install with: pip install pandas")

    records = parsed_data.get("records", [])
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Reorder columns for better display
    columns_order = [
        "date", "counterParty", "category", "type",
        "amount", "currency", "note"
    ]
    available_cols = [col for col in columns_order if col in df.columns]

    return df[available_cols]


def format_for_display(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format parsed data for UI display with currency formatting"""
    records = parsed_data.get("records", [])
    summary = parsed_data.get("summary", {})

    # Format amounts with currency
    currency = summary.get("currency", "")
    for record in records:
        amount = record.get("amount", 0)
        record["amount_formatted"] = f"{amount:,.2f} {currency}".strip()

    # Format summary
    summary_formatted = {
        "total_records": f"{summary.get('total_records', 0):,}",
        "total_expenses": f"{summary.get('total_expenses', 0):,.2f} {currency}".strip(),
        "total_income": f"{summary.get('total_income', 0):,.2f} {currency}".strip(),
        "net": f"{summary.get('net', 0):,.2f} {currency}".strip(),
        "period": summary.get("period", ""),
    }

    return {
        "records": records,
        "summary": summary_formatted,
        "pagination": parsed_data.get("pagination", {}),
    }


# Example usage
if __name__ == "__main__":
    # Sample response (minimal example)
    sample_response = [
        {
            "appliedRecordDateFilters": ["gte.2026-03-22T04:00:00.000Z"],
            "limit": 200,
            "nextOffset": 200,
            "offset": 0,
            "records": [
                {
                    "id": "610b317a-d227-4d87-a53e-697871ab7404",
                    "accountId": "fe1d441f-6180-47c4-a5ae-ec8e0ef197bc",
                    "note": "KFC Area Bory Sukova 2987/25, Plzen, 301 00, CZE",
                    "counterParty": "KFC Area Bory",
                    "amount": {"value": -489, "currencyCode": "CZK"},
                    "recordDate": "2026-11-01T23:00:00.000Z",
                    "category": {
                        "id": "5c5c03eb-000a-8000-8000-000000000000",
                        "name": "Food & Drinks",
                        "group": {"id": "food_and_drinks", "name": "Food & Drinks"},
                        "color": "#E74C3C"
                    }
                }
            ]
        }
    ]

    # Parse
    parsed = parse_wallet_response(sample_response)
    print("Parsed Records:")
    print(parsed["records"])
    print("\nSummary:")
    print(parsed["summary"])

    # To DataFrame
    if HAS_PANDAS:
        df = to_dataframe(parsed)
        print("\nDataFrame:")
        print(df)
    else:
        print("\n(DataFrame requires pandas: pip install pandas)")

    # Formatted for display
    formatted = format_for_display(parsed)
    print("\nFormatted for display:")
    print(formatted)
