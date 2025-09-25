import os
import io
import streamlit as st
import pandas as pd

from mycarbon_validator.loader import load_backend_validations
from mycarbon_validator.workflow import (
    build_validation_plan,
    validate_all,
)


def _inject_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="The Big Bad MyCarbon Excel Validator", layout="wide")
    _inject_css()

    st.title("The Big Bad Validator")
    st.caption("Version 0.5")

    # Backend validations file
    validation_sheet, error_messages = load_backend_validations()

    # Sidebar
    with st.sidebar:
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        st.header("Options")
        st.caption("Upload a file to validate all sheets. Once all sheets are validated, you can proceed to upload.")

    # === SECTION 1: Upload Excel ===
    with st.expander("1) Upload Excel file", expanded=True):
        uploaded = st.file_uploader("Select an Excel file (.xlsx)", type=["xlsx"])
        # Detect file change and reset state if a different file is uploaded
        if uploaded is not None:
            file_sig = f"{uploaded.name}:{getattr(uploaded, 'size', None)}"
            if st.session_state.get("last_file_sig") != file_sig:
                # New / different file -> clear previous success flags
                st.session_state["last_file_sig"] = file_sig
                for _k in ("upload_success", "validation_success", "validated_file_sig"):
                    if _k in st.session_state:
                        del st.session_state[_k]
        if uploaded is None:
            st.info("Upload an Excel file to begin.")
            return

        # Build validation plan from backend rules
        plan_df = build_validation_plan(validation_sheet)

        if plan_df.empty:
            st.error("Can't find the validation mapping.")
            return

        st.success(f"Loaded validation rules.")
        
        if plan_df is not None and not plan_df.empty and uploaded is not None:
            st.session_state.upload_success = True

    # === SECTION 3: Run Validation ===
    with st.expander("2) Run Validation", expanded=True):
        
        expanded = st.session_state.get("upload_success", False)
        if expanded:
            progress = st.progress(0, text="Starting validation…")

            progress_text = st.empty()
            total_items = len(plan_df)

            def _progress_callback(idx: int, total: int, sheet: str, result: dict):
                pct = idx / total
                status = "error" if result.get("error") else ("errors" if sum(result.get("counts", {}).values()) > 0 else "ok")
                label = f"Validating '{sheet}' ({idx}/{total}) - {status}"
                progress.progress(pct, text=label)
                progress_text.markdown(f"**Last processed:** `{sheet}` – status: {status}")

            overall_counts, per_sheet_results = validate_all(
                uploaded, validation_sheet, plan_df, progress_callback=_progress_callback
            )
            progress.progress(1.0, text="Validation complete.")

            # Summary
            st.subheader("Summary")
            if not any(r.get("counts") for r in per_sheet_results):
                st.session_state.validation_success = True
                # Bind success to this exact file signature so a new upload resets it
                st.session_state.validated_file_sig = st.session_state.get("last_file_sig")
                st.success("Congratulations, you have conquered the Big Bad Validator!")
            else:
                # Per error-type totals
                for etype, count in overall_counts.items():
                    msg_row = error_messages[error_messages["ErrorType"] == etype]
                    if not msg_row.empty:
                        msg = msg_row.iloc[0]["Message"]
                        st.write(f"- {msg}: {count} error(s) found")
                    else:
                        st.write(f"- {count} {etype.replace('_', ' ')} error(s) found")

                # Per-sheet quick table
                summary_rows = []
                for r in per_sheet_results:
                    total_errors = sum(r["counts"].values()) if r["counts"] else 0
                    missing_cols = r.get("missing_required", []) or []
                    status_label = (
                        "Failed to load/validate" if r["error"] else (
                            "Missing cols" if missing_cols else (
                                "Errors" if total_errors > 0 else "OK"
                            )
                        )
                    )
                    summary_rows.append({
                        "Sheet": r["Sheet"],
                        "TableName": r["TableName"],
                        "Errors": total_errors,
                        "MissingColumns": ", ".join(missing_cols),
                        "Status": status_label,
                    })
                st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

            # Per-sheet details
            st.subheader("Per-sheet Details")
            for r in per_sheet_results:
                total_errors = sum(r["counts"].values()) if r["counts"] else 0
                status_emoji = (
                    "⚠️" if r.get("error") else ("❌" if total_errors > 0 else "✅")
                )
                missing_cols = r.get("missing_required", []) or []
                missing_note = f"; missing {len(missing_cols)} column(s)" if missing_cols else ""
                exp_label = f"{r['Sheet']} {status_emoji} (" + (
                    f"errors: {total_errors}" if total_errors else "no validation errors"
                ) + missing_note + ")"
                expanded = (total_errors > 0) or bool(r.get("error"))
                with st.expander(exp_label, expanded=expanded):
                    st.caption(f"Sheet: {r['Sheet']} | Table: {r['TableName'] or '—'}")
                    if r["error"]:
                        st.error(r["error"])
                        continue

                    if missing_cols:
                        st.error(f"Missing required columns: {', '.join(missing_cols)}")

                    if not r["counts"] and not missing_cols:
                        st.success("No validation errors found for this sheet.")
                    elif r["counts"]:
                        # Error summary bullets (including missing_column counts already aggregated)
                        for etype, count in r["counts"].items():
                            msg_row = error_messages[error_messages["ErrorType"] == etype]
                            if not msg_row.empty:
                                msg = msg_row.iloc[0]["Message"]
                                st.write(f"- {msg}: {count} error(s) found")
                            else:
                                st.write(f"- {count} {etype.replace('_', ' ')} error(s) found")

                        # Styled table (preview)
                        css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
                        inline_css = ""
                        if os.path.exists(css_path):
                            try:
                                with open(css_path, "r", encoding="utf-8") as f:
                                    inline_css = f"<style>{f.read()}</style>"
                            except Exception:
                                inline_css = ""

                        wrapped_html = f"{inline_css}<div class=\"validation-report\">{r['html']}</div>"
                        st.components.v1.html(wrapped_html, height=500, scrolling=True)

                        # Downloads
                        html_buffer = io.BytesIO(r["html"].encode("utf-8"))
                        safe_sheet = str(r["Sheet"]).replace(" ", "_")
                        st.download_button(
                            label="Download this sheet's report (HTML)",
                            data=html_buffer,
                            file_name=f"validation_{safe_sheet}.html",
                            mime="text/html",
                        )


    # === SECTION 4: UPLOAD DATA ===
    with st.expander("3) Upload Data", expanded=True):
        current_sig = st.session_state.get("last_file_sig")
        success = st.session_state.get("validation_success", False)
        valid_for_this_file = success and (st.session_state.get("validated_file_sig") == current_sig)
        if valid_for_this_file:
            st.info("You have reached end-game!")
        else:
            st.caption("You need to level up first.")

if __name__ == "__main__":
    main()
