import pandas as pd
import json
from pathlib import Path


def _resolve_excel_path(excel_name: str) -> Path:
    """Resolve the Excel input path across supported locations."""
    if not excel_name or not excel_name.strip():
        raise ValueError('EXCEL_NAME is empty. Set EXCEL_NAME in your .env file.')

    raw = Path(excel_name.strip())
    if raw.is_absolute() and raw.exists():
        return raw

    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir / 'resources' / raw.name,
        module_dir.parent / 'resources' / raw.name,
        Path.cwd() / 'resources' / raw.name,
        Path.cwd() / raw.name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    available = sorted((module_dir / 'resources').glob('*.xlsx')) if (module_dir / 'resources').exists() else []
    available_names = ', '.join(p.name for p in available) if available else 'none'
    raise FileNotFoundError(
        f'Excel file not found for EXCEL_NAME="{excel_name}". '
        f'Looked in src/resources, resources, and current directory. '
        f'Available src/resources files: {available_names}'
    )

def complete_stocks_list_extractor(excel_name: str = '',
                                   output_json: str = 'stocksdict.json') -> None:

    excel_path = _resolve_excel_path(excel_name)
    print(f"Extracting stock data from {excel_path} and saving to {output_json}")
    list_of_companies = pd.read_excel(excel_path)
    stocksdict = {
        "largestocks": [],
        "midstocks": [],
        "smallstocks": []
    }

    capitalization_col = [col for col in list_of_companies.columns if ('market capital' in col.lower() or 'in lakh' in col.lower())][0]
    if 'Symbol' not in list_of_companies.columns or 'Company Name' not in list_of_companies.columns:
        raise KeyError('Excel must contain both "Symbol" and "Company Name" columns.')

    # Normalize market cap values (commas/text) into numeric lakhs.
    list_of_companies[capitalization_col] = pd.to_numeric(
        list_of_companies[capitalization_col]
        .astype(str)
        .str.replace(',', '', regex=False)
        .str.replace(r'[^0-9.\-]', '', regex=True),
        errors='coerce'
    )

    print(f"Using capitalization column: {capitalization_col}")
    skipped_rows = 0
    for index, company in list_of_companies.iterrows():
        market_value = company[capitalization_col]
        if pd.isna(market_value):
            skipped_rows += 1
            continue

        stock_code = company['Symbol']
        stock_full_name = company['Company Name']
        if market_value > 2000000:
            stocksdict['largestocks'].append({stock_code: stock_full_name})
        elif market_value < 2000000 and market_value > 500000:
            stocksdict['midstocks'].append({stock_code: stock_full_name})
        elif market_value < 500000:
            stocksdict['smallstocks'].append({stock_code: stock_full_name})

    if skipped_rows:
        print(f"Skipped {skipped_rows} rows due to invalid market cap values.")

    # Serializing json
    stocksdict_json_object = json.dumps(stocksdict, indent=4)
    
    # Writing to stocksdict.json
    with open(output_json, "w") as stocksdictoutfile:
        stocksdictoutfile.write(stocksdict_json_object)