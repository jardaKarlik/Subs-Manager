# Wallet Data Table Parser

Python module to parse wallet API responses and convert them to data table format.

## Functions

### `parse_wallet_response(response_data: List[Dict]) -> Dict`
Main parser that transforms the wallet API response into structured data.

**Input**: Raw API response (list with single dict)
**Output**: Dict with `records`, `summary`, and `pagination`

```python
from wallet_data_table import parse_wallet_response

api_response = [...]  # From HTTP Request node
parsed = parse_wallet_response(api_response)

# Access data
records = parsed["records"]        # List of flattened records
summary = parsed["summary"]        # Totals and statistics
pagination = parsed["pagination"]  # Pagination info
```

### `format_for_display(parsed_data: Dict) -> Dict`
Format parsed data with currency formatting for UI display.

```python
from wallet_data_table import parse_wallet_response, format_for_display

parsed = parse_wallet_response(api_response)
formatted = format_for_display(parsed)

# Records now have 'amount_formatted' field
# Summary has currency-formatted values
```

### `to_dataframe(parsed_data: Dict) -> pd.DataFrame`
Convert to pandas DataFrame (requires `pandas` installed).

```python
import pandas as pd
from wallet_data_table import parse_wallet_response, to_dataframe

parsed = parse_wallet_response(api_response)
df = to_dataframe(parsed)  # Requires: pip install pandas
```

## Record Structure

Each parsed record contains:
- `date` - Formatted date (YYYY-MM-DD)
- `type` - Transaction type (expense/income/transfer)
- `amount` - Absolute amount value
- `currency` - Currency code (CZK, EUR, etc.)
- `counterParty` - Merchant/payee name
- `category` - Category name
- `category_group` - Category group name
- `category_color` - Hex color code
- `note` - Additional notes
- `recordId` - Unique record ID

## Summary Statistics

- `total_records` - Number of transactions
- `total_expenses` - Sum of all expenses
- `total_income` - Sum of all income
- `net` - Income minus expenses
- `currency` - Primary currency code
- `period` - Period description

## Pagination

- `offset` - Current offset
- `limit` - Records per page
- `nextOffset` - Offset for next page (or null if no more)
- `hasMore` - Boolean indicating more pages available

## Usage in n8n Workflow

1. **HTTP Request node** returns raw API response
2. **Code node** (JavaScript) calls Python via exec or external API
3. **Data table** displays formatted results

### Example n8n Code Node (Node.js)
```javascript
const { exec } = require('child_process');

// Pass API response to Python script
const pyScript = `
from wallet_data_table import parse_wallet_response, format_for_display
import json

response = ${JSON.stringify($input.first().json)}
parsed = parse_wallet_response([response])
formatted = format_for_display(parsed)
print(json.dumps(formatted))
`;

// Execute Python and return results
exec(\`python3 -c "\${pyScript}"\`, (error, stdout, stderr) => {
  if (error) return [{json: {error: stderr}}];
  const result = JSON.parse(stdout);
  return [{json: result}];
});
```

## Installation

```bash
# Core functionality (no dependencies)
python3 wallet_data_table.py

# Optional: Add pandas for DataFrame support
pip install pandas
```

## Testing

```bash
python3 wallet_data_table.py
```

Shows sample output with parsed records, summary, and formatted data.
