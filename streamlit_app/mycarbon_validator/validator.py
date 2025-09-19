from __future__ import annotations

import pandas as pd


def select_validation_columns(df: pd.DataFrame, validation_rules: pd.DataFrame, sheet: str) -> pd.DataFrame:
    rules_for_sheet = validation_rules[validation_rules['Sheet'] == sheet]
    required_columns = rules_for_sheet['Column'].tolist()
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"The following required columns are missing from the DataFrame: {missing}")
    return df[required_columns]


def find_validation_errors(data_sheet: pd.DataFrame, validation_rules: pd.DataFrame, sheet: str) -> dict:
    rules_for_sheet = validation_rules[validation_rules['Sheet'] == sheet]
    error_cells: dict = {}

    for _, rule in rules_for_sheet.iterrows():
        column_name = rule['Column']
        if column_name not in data_sheet.columns:
            continue

        column_data = data_sheet[column_name]
        expected_type = str(rule['Datatype']).lower()
        is_required = rule['Required']
        allows_blanks = rule['AllowBlanks']

        if is_required:
            empty_mask = column_data.isna() | (column_data == '')
            for idx in data_sheet.index[empty_mask]:
                error_cells[(idx, column_name)] = "empty_required"

        if not allows_blanks:
            blank_indicators = [
                'N/A', 'n/a', '#N/A', '#n/a', 'NA#', 'na#', '#NA', '#na',
                'NULL', 'null'
            ]
            for i, value in enumerate(column_data):
                if pd.isna(value):
                    continue
                if str(value).strip() in blank_indicators:
                    row_idx = data_sheet.index[i]
                    error_cells[(row_idx, column_name)] = "blank_indicator"

        blank_indicators = [
            'N/A', 'n/a', '#N/A', '#n/a', 'NA#', 'na#', '#NA', '#na',
            'NULL', 'null'
        ]
        valid_mask = (~column_data.isna() & (column_data != '') &
                      ~column_data.astype(str).str.strip().isin(blank_indicators))
        clean_data = column_data[valid_mask]
        clean_indices = data_sheet.index[valid_mask].tolist()

        if len(clean_data) > 0:
            if expected_type == 'year':
                for idx, value in zip(clean_indices, clean_data):
                    try:
                        year = int(float(str(value)))
                        if not (1900 <= year <= 2100):
                            error_cells[(idx, column_name)] = "invalid_year"
                    except Exception:
                        error_cells[(idx, column_name)] = "invalid_year"
            elif expected_type in ['int', 'integer']:
                for idx, value in zip(clean_indices, clean_data):
                    try:
                        int(float(str(value)))
                    except Exception:
                        error_cells[(idx, column_name)] = "invalid_integer"
            elif expected_type in ['float', 'number', 'numeric']:
                for idx, value in zip(clean_indices, clean_data):
                    try:
                        float(str(value))
                    except Exception:
                        error_cells[(idx, column_name)] = "invalid_float"
            elif expected_type in ['bool', 'boolean']:
                valid_boolean_values = [
                    'true', 'false', 'y', 'n', 'yes', 'no',
                    '1', '0', 'True', 'False', 'Y', 'N',
                    'Yes', 'No', 'TRUE', 'FALSE', 'YES', 'NO'
                ]
                for idx, value in zip(clean_indices, clean_data):
                    if isinstance(value, bool):
                        continue
                    str_value = str(value).strip()
                    if str_value not in valid_boolean_values:
                        error_cells[(idx, column_name)] = "invalid_boolean"

    return error_cells
