from __future__ import annotations

from typing import Optional, Tuple, Dict, Any, Callable

import pandas as pd

from .loader import load_excel_data
from .validator import select_validation_columns, find_validation_errors
from .styling import style_errors_as_html, summarize_errors


def build_validation_plan(validation_sheet: pd.DataFrame) -> pd.DataFrame:
    """Return unique pairs of (Sheet, TableName?) that define the validation plan.
    Ensures Sheet is string-typed and drops blanks.
    """
    if "Sheet" not in validation_sheet.columns:
        return pd.DataFrame(columns=["Sheet", "TableName"]).astype({"Sheet": str})

    if "TableName" in validation_sheet.columns:
        plan_df = validation_sheet[["Sheet", "TableName"]].copy()
    else:
        plan_df = validation_sheet[["Sheet"]].copy()
        plan_df["TableName"] = None

    plan_df = plan_df.dropna(subset=["Sheet"])  # ignore blanks
    plan_df["Sheet"] = plan_df["Sheet"].astype(str)
    plan_df = plan_df.drop_duplicates().reset_index(drop=True)
    return plan_df


def derive_table_for_sheet(validation_sheet: pd.DataFrame, sheet: str) -> Optional[str]:
    """Return a single TableName for a given sheet if present; otherwise None.
    """
    if "TableName" not in validation_sheet.columns or "Sheet" not in validation_sheet.columns:
        return None
    candidates = (
        validation_sheet.loc[validation_sheet["Sheet"].astype(str) == str(sheet), "TableName"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    return candidates[0] if candidates else None


def validate_one_sheet(
    file_or_path,
    validation_sheet: pd.DataFrame,
    sheet: str,
    table_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate a single sheet/table from the uploaded file.
    Returns a result dict with keys: Sheet, TableName, error, counts, html
    """
    # Load data (table or sheet)
    try:
        df_loaded = load_excel_data(
            file_or_path, sheet_name=sheet, table_name=table_name if table_name else None
        )
    except Exception as e:
        # If table is missing, attempt a graceful fallback to full-sheet read
        msg = str(e)
        raise ValueError(msg) from e

    # Restrict to validation columns for this sheet
    df_for_validation = select_validation_columns(df_loaded, validation_sheet, sheet)
    missing_required = df_for_validation.attrs.get('missing_required', [])

    # Run validations and build presentation
    error_cells = find_validation_errors(df_for_validation, validation_sheet, sheet)
    counts = summarize_errors(error_cells)
    html_table = style_errors_as_html(df_for_validation, error_cells)

    return {
        "Sheet": sheet,
        "TableName": table_name,
        "error": None,
        "counts": counts,
        "html": html_table,
        "missing_required": missing_required,
    }

def validate_all(
    file_or_path,
    validation_sheet: pd.DataFrame,
    plan_df: Optional[pd.DataFrame] = None,
    progress_callback: Optional[Callable[[int, int, str, Dict[str, Any]], None]] = None,
) -> Tuple[Dict[str, int], list[Dict[str, Any]]]:
    """Validate all sheets/tables in the plan and return (overall_counts, per_sheet_results).

    Parameters
    ----------
    file_or_path : UploadedFile | str | BytesIO
        The uploaded file-like object or a filesystem path.
    validation_sheet : DataFrame
        Backend validation mapping sheet.
    plan_df : DataFrame, optional
        Pre-built plan of sheets/tables to validate. Built internally if omitted.
    progress_callback : callable(idx:int, total:int, sheet:str, result:dict), optional
        If provided, called after each sheet is processed (whether success or failure).
    """
    if plan_df is None:
        plan_df = build_validation_plan(validation_sheet)

    overall_counts: Dict[str, int] = {}
    per_sheet_results: list[Dict[str, Any]] = []

    total = len(plan_df)
    for idx, (_, row) in enumerate(plan_df.iterrows(), start=1):
        sheet = row["Sheet"]
        table = row.get("TableName") if "TableName" in row else None
        table = None if (pd.isna(table) if hasattr(pd, 'isna') else table is None) else table

        # Reset pointer for file-like objects so each read starts fresh.
        if hasattr(file_or_path, "seek"):
            try:
                file_or_path.seek(0)
            except Exception:
                pass

        try:
            result = validate_one_sheet(file_or_path, validation_sheet, sheet, table)
        except Exception as e:
            msg = str(e)
            counts: Dict[str, int] = {}
            if "SHEET_NOT_FOUND:" in msg:
                counts["sheet_not_found"] = 1
            elif "TABLE_NOT_FOUND:" in msg:
                counts["table_not_found"] = 1
            result = {
                "Sheet": sheet,
                "TableName": table,
                "error": msg,
                "counts": counts,
                "html": "",
                "missing_required": [],
            }
        per_sheet_results.append(result)

        for et, c in result.get("counts", {}).items():
            overall_counts[et] = overall_counts.get(et, 0) + c

        if progress_callback:
            try:
                progress_callback(idx, total, sheet, result)
            except Exception:
                # Never let UI callback failure break core validation
                pass

    return overall_counts, per_sheet_results
