import os
import io
import streamlit as st
import pandas as pd

from mycarbon_validator.config import CLIENT_DATA_PATH, DEFAULT_SCOPE, DEFAULT_TABLE
from mycarbon_validator.loader import load_excel_data, load_backend_validations
from mycarbon_validator.validator import select_validation_columns, find_validation_errors
from mycarbon_validator.styling import style_errors_as_html, summarize_errors


def _inject_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="The Big Bad MyCarbon Excel Validator", layout="wide")
    _inject_css()

    st.title("The Big Bad MyCarbon Excel Validator")
    st.caption("Version 0.1")

    # Backend validations (not editable by user)
    validation_sheet, error_messages = load_backend_validations(CLIENT_DATA_PATH)

    # Sidebar
    with st.sidebar:
        logo_path = os.path.join("assets", "logo.png")  # relative to your app root
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)

        st.header("Options")
        scope_options = []
        if "Sheet" in validation_sheet.columns:
            scope_options = (
                pd.Series(validation_sheet["Sheet"])
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )
            scope_options.sort()

        if scope_options:
            default_index = (
                scope_options.index(DEFAULT_SCOPE)
                if DEFAULT_SCOPE in scope_options
                else 0
            )
            scope = st.selectbox(
                "Scope (sheet name)", options=scope_options, index=default_index
            )
        else:
            scope = st.text_input("Scope (sheet name)", value=DEFAULT_SCOPE)

        table_name = st.text_input("Excel table name", value=DEFAULT_TABLE)

    # === SECTION 1: Upload Excel ===
    with st.expander("1) Upload Excel file", expanded=True):
        uploaded = st.file_uploader("Select an Excel file (.xlsx)", type=["xlsx"])

        if uploaded is None:
            st.info("Upload an Excel file to begin.")
            return

        try:
            df_uploaded = load_excel_data(
                uploaded, sheet_name=scope, table_name=table_name
            )
        except Exception as e:
            st.error(f"Failed to read Excel: {e}")
            return

        st.success(f"Loaded {len(df_uploaded)} rows and {len(df_uploaded.columns)} columns.")
        st.dataframe(df_uploaded.head(20), use_container_width=True)

        try:
            df_for_validation = select_validation_columns(df_uploaded, validation_sheet, scope)
            st.success("Columns selected successfully for validation.")
        except Exception as e:
            st.error(str(e))
            return

    # === SECTION 3: Run Validation ===
    with st.expander("3) Run Validation", expanded=True):
        run = st.button("Run Validation", type="primary")
        if run:
            with st.spinner("Validating…"):
                error_cells = find_validation_errors(df_for_validation, validation_sheet, scope)
                html_table = style_errors_as_html(df_for_validation, error_cells)
                counts = summarize_errors(error_cells)

            # Summary
            st.subheader("Summary")
            if not error_cells:
                st.success("No validation errors found!")
            else:
                for etype, count in counts.items():
                    msg_row = error_messages[error_messages["ErrorType"] == etype]
                    if not msg_row.empty:
                        msg = msg_row.iloc[0]["Message"]
                        st.write(f"- {msg}: {count} error(s) found")
                    else:
                        st.write(f"- {count} {etype.replace('_', ' ')} error(s) found")

            # Validation Results
            st.subheader("Validation Results")
            css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
            inline_css = ""
            if os.path.exists(css_path):
                try:
                    with open(css_path, "r", encoding="utf-8") as f:
                        inline_css = f"<style>{f.read()}</style>"
                except Exception:
                    inline_css = ""

            wrapped_html = f"{inline_css}<div class=\"validation-report\">{html_table}</div>"
            st.components.v1.html(wrapped_html, height=600, scrolling=True)

            # Downloads
            html_buffer = io.BytesIO(html_table.encode("utf-8"))
            st.download_button(
                label="Download validation report (HTML)",
                data=html_buffer,
                file_name="validation_report.html",
                mime="text/html",
            )


if __name__ == "__main__":
    main()
