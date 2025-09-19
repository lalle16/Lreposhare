import os


# Mirror notebook defaults
CLIENT_DATA_PATH = r"C:\\Users\\navns\\OneDrive - insightsandcoffee.com\\Data\\Client data\\mycarbon"
DEFAULT_SCOPE = "Scope 1"
DEFAULT_TABLE = "Scope1Calcs"


def get_validations_excel_path(base_path: str | None = None) -> str:
    base = base_path or CLIENT_DATA_PATH
    return os.path.join(base, "Validations", "validations.xlsx")
