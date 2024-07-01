from datetime import datetime
import os
from typing import List
from loguru import logger
import pandas as pd
from pydantic import BaseModel
import requests


class GoogleSheetsData(BaseModel):
    sheet_name: str
    data_frame: pd.DataFrame

    class Config:
        arbitrary_types_allowed = True


def get_objection_handelling_vars() -> tuple[str, str]:
    # Your Google Sheets API key
    API_KEY = os.getenv("GOOGLE_API_KEY", None)

    # The ID of your Google Sheet
    SHEET_ID = os.getenv("OBJ_HANDLE_SHEET_ID", None)

    if not API_KEY or not SHEET_ID:
        if not API_KEY:
            logger.error("API_KEY not found")
        if not SHEET_ID:
            logger.error("SHEET_ID not found")
    return API_KEY, SHEET_ID


def get_google_file_modified_time(file_id: str, api_key: str) -> datetime:
    url_modified_time = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=modifiedTime&key={api_key}"
    response_modified_time = requests.get(url_modified_time, timeout=10)
    modified_time = response_modified_time.json().get("modifiedTime", None)
    if not modified_time:
        logger.error(
            f"Error fetching modified time: {response_modified_time.status_code}"
        )
        raise requests.exceptions.HTTPError(
            f"Error fetching modified time: {response_modified_time.status_code}"
        )
    else:
        # convert to datetime object
        iso_string = modified_time.replace("Z", "+00:00")
        modified_time = datetime.fromisoformat(iso_string)
        return modified_time


def get_google_sheets_data(sheet_id: str, api_key: str) -> List[GoogleSheetsData]:

    # Construct the URL
    url_metadata = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?key={api_key}"
    )

    # Make the request
    response_metadata = requests.get(url_metadata, timeout=10)

    # Check the response
    if response_metadata.status_code == 200:
        metadata = response_metadata.json()
        logger.debug(f"metadata: {metadata}")
        sheets = metadata.get("sheets", [])
        logger.debug(f"sheets: {sheets}")

        # Collect data from all sheets
        all_data = []
        for sheet in sheets:
            sheet_title = sheet["properties"]["title"]
            url_data = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{sheet_title}?key={api_key}"
            response_data = requests.get(url_data, timeout=10)
            if response_data.status_code == 200:
                sheet_data = response_data.json()
                values = sheet_data.get("values", [])
                # Convert values to a DataFrame
                df = pd.DataFrame(values)
                # Set the first row as the header if desired
                df.columns = df.iloc[0]
                df = df[1:]
                data = GoogleSheetsData(sheet_name=sheet_title, data_frame=df)
                all_data.append(data)
            else:
                logger.error(
                    f"Error fetching data for sheet {sheet_title}: {response_data.status_code}"
                )
        logger.debug(f"\n{all_data}")

        return all_data
    else:
        logger.error(f"Error fetching metadata: {response_metadata.status_code}")
