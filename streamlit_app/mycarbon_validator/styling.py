from __future__ import annotations

from pathlib import Path
from html import escape
import pandas as pd

def style_errors_as_html(df: pd.DataFrame, error_cells: dict) -> str:
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    for (row_idx, col_name), error_type in error_cells.items():
        # Skip pseudo missing-column entries (-1 row index) for cell styling
        if row_idx not in styles.index or col_name not in styles.columns:
            continue
        if error_type == 'empty_required':
            styles.loc[row_idx, col_name] = 'background-color: #ff6b6b; color: white; font-weight: bold'
        elif error_type == 'blank_indicator':
            styles.loc[row_idx, col_name] = 'background-color: #ff8787; color: white; font-weight: bold'
        elif error_type.startswith('invalid_'):
            styles.loc[row_idx, col_name] = 'background-color: #ffa8a8; color: black; font-weight: bold'
        # 'missing_column' not styled at cell level because column absent

    styled = (
        df.style
        .apply(lambda _: styles, axis=None)
        .set_caption(f"Validation Results - {len(error_cells)} error cells found")
    )
    return styled.to_html()

def build_validation_report_html(
    counts: dict,
    error_messages: pd.DataFrame,
    html_table: str,
    css_path: str | None = None,
    title: str = "Validation Report"
) -> str:
    """Return a full HTML report (string)."""
    css = ""
    if css_path and Path(css_path).exists():
        css = Path(css_path).read_text(encoding="utf-8")

    # Summary block
    if not counts:
        summary_html = "<p>No validation errors found!</p>"
    else:
        items = []
        for etype, count in counts.items():
            row = error_messages[error_messages["ErrorType"] == etype]
            if not row.empty:
                msg = escape(str(row.iloc[0]["Message"]))
                items.append(f"<li>{msg}: {count} error(s) found</li>")
            else:
                items.append(f"<li>{count} {escape(etype.replace('_',' '))} error(s) found</li>")
        summary_html = "<ul>" + "".join(items) + "</ul>"

    return summary_html



def summarize_errors(error_cells: dict) -> dict:
    counts: dict[str, int] = {}
    for error_type in error_cells.values():
        counts[error_type] = counts.get(error_type, 0) + 1
    return counts
