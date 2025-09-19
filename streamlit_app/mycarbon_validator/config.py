import os

# Always point to the directory where this script lives
APP_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_SCOPE = "Scope 1"
DEFAULT_TABLE = "Scope1Calcs"


def get_validations_excel_path() -> str:
    """Return the absolute path to validations.xlsx in the same folder as this app."""
    return os.path.join(APP_DIR, "validations.xlsx")
