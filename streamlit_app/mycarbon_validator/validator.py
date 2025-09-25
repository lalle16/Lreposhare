from __future__ import annotations

import pandas as pd


def select_validation_columns(df: pd.DataFrame, validation_rules: pd.DataFrame, sheet: str) -> pd.DataFrame:
    """Return only the columns required for validation for a given sheet.

    Attach a list of missing column names.
    """
    rules_for_sheet = validation_rules[validation_rules['Sheet'] == sheet]
    required_columns = rules_for_sheet['Column'].tolist()
    missing = [col for col in required_columns if col not in df.columns]
    present = [col for col in required_columns if col in df.columns]
    subset = df[present].copy() if present else df.iloc[0:0].copy()
    subset.attrs['missing_required'] = missing
    return subset


def find_validation_errors(data_sheet: pd.DataFrame, validation_rules: pd.DataFrame, sheet: str) -> dict:
    """Return a dict mapping (row_index, column_name) -> error_type.

    Also emits a 'missing_column' error_type for each required column absent
    from the uploaded sheet. Row index is set to -1 for such pseudo-cells.
    """
    rules_for_sheet = validation_rules[validation_rules['Sheet'] == sheet]
    error_cells: dict = {}

    # Handle missing required columns (attached by select_validation_columns)
    missing_required = data_sheet.attrs.get('missing_required', [])
    for col in missing_required:
        error_cells[(-1, col)] = 'missing_column'

    for _, rule in rules_for_sheet.iterrows():
        column_name = rule['Column']
        if column_name not in data_sheet.columns:
            # Already recorded as missing if required; skip further checks
            continue

        column_data = data_sheet[column_name]
        expected_type = str(rule['Datatype']).lower()
        is_required = rule['Required']
        allows_blanks = rule['AllowBrokenRefs']

        # Empty required cells
        if is_required:
            empty_mask = column_data.isna() | (column_data == '')
            for idx in data_sheet.index[empty_mask]:
                error_cells[(idx, column_name)] = 'empty_required'

        # Unified blank indicator list (includes the disallowed placeholders)
        blank_indicators = [
            'N/A', 'n/a', '#N/A', '#n/a', 'NA#', 'na#', '#NA', '#na',
            'NULL', 'null', '#ERROR', '#Error'
        ]

        # Disallowed blank indicators
        if not allows_blanks:
            for i, value in enumerate(column_data):
                if pd.isna(value):
                    continue
                if str(value).strip() in blank_indicators:
                    row_idx = data_sheet.index[i]
                    error_cells[(row_idx, column_name)] = 'blank_indicator'

        # Prepare cleaned subset for type validation (exclude all indicators except we don't add '#ERROR' duplicates here)
        valid_mask = (~column_data.isna() & (column_data != '') &
                      ~column_data.astype(str).str.strip().isin(blank_indicators))
        clean_data = column_data[valid_mask]
        clean_indices = data_sheet.index[valid_mask].tolist()

        if len(clean_data) == 0:
            continue

        if expected_type == 'year':
            for idx, value in zip(clean_indices, clean_data):
                try:
                    year = int(float(str(value)))
                    if not (1900 <= year <= 2100):
                        error_cells[(idx, column_name)] = 'invalid_year'
                except Exception:
                    error_cells[(idx, column_name)] = 'invalid_year'
        elif expected_type in ['int', 'integer']:
            for idx, value in zip(clean_indices, clean_data):
                try:
                    int(float(str(value)))
                except Exception:
                    error_cells[(idx, column_name)] = 'invalid_integer'
        elif expected_type in ['float', 'number', 'numeric']:
            for idx, value in zip(clean_indices, clean_data):
                try:
                    float(str(value))
                except Exception:
                    error_cells[(idx, column_name)] = 'invalid_float'
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
                    error_cells[(idx, column_name)] = 'invalid_boolean'

    return error_cells
