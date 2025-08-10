import os
from dotenv import load_dotenv

load_dotenv()

cfg = {
    "airtable": {
        "apiKey": os.getenv("AIRTABLE_PERSONAL_ACCESS_TOKEN"),
        "baseId": os.getenv("AIRTABLE_BASE_ID"),
        "tableName": os.getenv("AIRTABLE_TABLE_NAME"),
        "viewId": os.getenv("AIRTABLE_VIEW_ID"),
        "tableId": os.getenv("AIRTABLE_TABLE_ID"),
    },
    "adspower": {
        "apiUrl": os.getenv("ADSPOWER_API_URL"),
        "apiKey": os.getenv("ADSPOWER_API_KEY"),
    },
    "settings": {"logToFile": os.getenv("LOG_TO_FILE")},
}


def get_cfg():
    return cfg
