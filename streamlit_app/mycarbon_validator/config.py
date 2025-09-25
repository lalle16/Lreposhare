import os

# Always point to the directory where this script lives
client_data_path = os.path.dirname(os.path.abspath(__file__))

def get_validations_excel_path():
    """Return the absolute path to validations.xlsx in the same folder as this app."""
    return os.path.join(client_data_path, "validations.xlsx")
