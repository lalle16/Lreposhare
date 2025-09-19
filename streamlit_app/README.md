# MyCarbon Excel Validator (Streamlit)

UI in `app.py`
Validation logic in `mycarbon_validator/`
CSS in `assets/styles.css` (put `assets/logo.png` to show a logo)

Run locally:

```bash
cd "c:/Users/navns/OneDrive - insightsandcoffee.com/Codespace/Clients/mycarbon/streamlit_app"
pip install -r requirements.txt
streamlit run app.py
```

Backend validation sheets (not user editable) are read from:
`C:\\Users\\navns\\OneDrive - insightsandcoffee.com\\Data\\Client data\\mycarbon\\Validations\\validations.xlsx`

Defaults for scope and table are `TestScope` and `TestScopeCalcs`. Change in `mycarbon_validator/config.py` if needed.