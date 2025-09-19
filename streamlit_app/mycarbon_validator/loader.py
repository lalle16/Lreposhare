from __future__ import annotations

import io
import os
from typing import Tuple

import openpyxl
import pandas as pd

from .config import get_validations_excel_path


def load_excel_data(file_or_path, sheet_name: str | None = None, table_name: str | None = None) -> pd.DataFrame:
    """
    Load an Excel file, optionally from a specific sheet or named table.
    - If table_name is None, load the sheet from row 0 (header row).
    - If table_name is provided, load only the named table from the sheet.
    Accepts a file-like object (as provided by Streamlit) or a path.
    """

    if table_name is not None:
        # Use openpyxl to find the named table range
        if hasattr(file_or_path, "read"):
            data_bytes = file_or_path.read()
            wb = openpyxl.load_workbook(io.BytesIO(data_bytes), data_only=True)
        else:
            wb = openpyxl.load_workbook(file_or_path, data_only=True)

        ws = wb[sheet_name] if sheet_name else wb.active
        if table_name not in ws.tables:
            raise ValueError(f"Table '{table_name}' not found in sheet '{ws.title}'")
        table = ws.tables[table_name]
        ref = table.ref  # e.g., 'B2:F10'
        min_col, min_row, max_col, max_row = openpyxl.utils.range_boundaries(ref)
        data = ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col, values_only=True)
        data = list(data)
        header = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=header)
        return df

    # No table name: let pandas read the sheet
    if hasattr(file_or_path, "read"):
        if sheet_name is None:
            df = pd.read_excel(io.BytesIO(file_or_path.getvalue()), header=0)
        else:
            df = pd.read_excel(io.BytesIO(file_or_path.getvalue()), sheet_name=sheet_name, header=0)
    else:
        if sheet_name is None:
            df = pd.read_excel(file_or_path, header=0)
        else:
            df = pd.read_excel(file_or_path, sheet_name=sheet_name, header=0)
    return df


def load_backend_validations(client_data_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load validation rules and error messages from the backend validations.xlsx.
    These are not user-editable in the app.
    Returns (validation_sheet, error_messages)
    """
    validations_path = get_validations_excel_path(client_data_path)
    validation_sheet = pd.read_excel(validations_path, sheet_name="Columns", header=0)
    error_messages = pd.read_excel(validations_path, sheet_name="Messages", header=0)
    return validation_sheet, error_messages
