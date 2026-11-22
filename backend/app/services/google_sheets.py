import os
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.models.influencer import Influencer

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    Credentials = None

class GoogleSheetsService:
    def __init__(self):
        self.credentials_file = settings.GOOGLE_SHEETS_CREDENTIALS_FILE
        self.spreadsheet_id = settings.GOOGLE_SPREADSHEET_ID
        self.client = None
        self._init_client()

    def _init_client(self):
        if not gspread or not Credentials:
            logger.info("Google Sheets packages not available or not installed.")
            return

        if os.path.exists(self.credentials_file):
            try:
                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
                creds = Credentials.from_service_account_file(self.credentials_file, scopes=scopes)
                self.client = gspread.authorize(creds)
                logger.info("Google Sheets client initialized with service account.")
            except Exception as e:
                logger.error(f"Failed to authenticate with Google Sheets service account: {e}")

    def is_configured(self) -> bool:
        return bool(self.client and self.spreadsheet_id)

    async def sync_influencers(
        self,
        influencers: List[Influencer],
        spreadsheet_id: Optional[str] = None,
        outreach_metadata: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Upserts influencer records by database ID in Google Sheets or the local archive.
        If Google API credentials are not set or unavailable, seamlessly writes to local
        simulated sheet export file and flags records as synced.
        """
        target_sheet_id = spreadsheet_id or self.spreadsheet_id
        
        # Prepare tabular data
        headers = [
            "ID",
            "Influencer Name",
            "Instagram Username",
            "Profile URL",
            "Niche",
            "Followers",
            "Business Email",
            "Location",
            "Lead Status",
            "Suitability Score",
            "AI Category",
            "AI Summary",
            "Match Reason",
            "Campaign Name",
            "Opted Out",
            "Last Contacted",
            "Latest Outreach Campaign",
            "Latest Email Subject",
            "Latest Email Status",
            "Latest Email Sent At",
            "Latest Reply Classification",
            "Latest Reply Received At",
            "Synced Timestamp"
        ]

        rows = {}
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for inf in influencers:
            outreach = (outreach_metadata or {}).get(inf.id, {})
            rows[inf.id] = {
                "ID": inf.id,
                "Influencer Name": inf.name,
                "Instagram Username": f"@{inf.instagram_username}",
                "Profile URL": inf.profile_url,
                "Niche": inf.niche,
                "Followers": inf.followers_count,
                "Business Email": inf.email or "N/A",
                "Location": inf.location,
                "Lead Status": inf.status,
                "Suitability Score": inf.suitability_score if inf.suitability_score is not None else "Not Analyzed",
                "AI Category": inf.category or "N/A",
                "AI Summary": inf.profile_summary or "N/A",
                "Match Reason": inf.match_reason or "N/A",
                "Campaign Name": inf.campaign_name or "General Campaign",
                "Opted Out": "Yes" if getattr(inf, "opted_out", False) else "No",
                "Last Contacted": (
                    inf.last_contacted_at.strftime("%Y-%m-%d %H:%M:%S")
                    if getattr(inf, "last_contacted_at", None)
                    else "N/A"
                ),
                "Latest Outreach Campaign": outreach.get("campaign_name", "N/A"),
                "Latest Email Subject": outreach.get("subject", "N/A"),
                "Latest Email Status": outreach.get("status", "N/A"),
                "Latest Email Sent At": outreach.get("sent_at", "N/A"),
                "Latest Reply Classification": outreach.get("reply_classification", "N/A"),
                "Latest Reply Received At": outreach.get("reply_received_at", "N/A"),
                "Synced Timestamp": now_str,
            }

        # If live Google Sheets is configured, push to it
        if self.client and target_sheet_id:
            try:
                sheet = self.client.open_by_key(target_sheet_id).sheet1
                existing_values = sheet.get_all_values()
                if not existing_values:
                    sheet.append_row(headers, value_input_option="RAW")
                    sheet_headers = headers
                    existing_values = [headers]
                else:
                    sheet_headers = list(existing_values[0])
                    missing_headers = [header for header in headers if header not in sheet_headers]
                    if missing_headers:
                        sheet_headers.extend(missing_headers)
                        last_column = self._column_label(len(sheet_headers))
                        sheet.update(
                            range_name=f"A1:{last_column}1",
                            values=[sheet_headers],
                            value_input_option="RAW",
                        )

                existing_rows = {}
                id_column = sheet_headers.index("ID")
                for row_number, values in enumerate(existing_values[1:], start=2):
                    if len(values) > id_column and values[id_column]:
                        existing_rows.setdefault(str(values[id_column]), []).append(row_number)

                last_column = self._column_label(len(sheet_headers))
                for influencer_id, row_data in rows.items():
                    row = [row_data.get(header, "") for header in sheet_headers]
                    row_numbers = existing_rows.get(str(influencer_id), [])
                    if row_numbers:
                        for row_number in row_numbers:
                            sheet.update(
                                range_name=f"A{row_number}:{last_column}{row_number}",
                                values=[row],
                                value_input_option="RAW",
                            )
                    else:
                        sheet.append_row(row, value_input_option="RAW")

                logger.info(f"Successfully upserted {len(rows)} records to Google Sheet: {target_sheet_id}")
                return {
                    "success": True,
                    "mode": "live_google_sheets",
                    "synced_count": len(rows),
                    "spreadsheet_id": target_sheet_id,
                    "message": f"Successfully updated {len(rows)} influencer records in Google Sheets."
                }
            except Exception as e:
                logger.error(f"Live Google Sheets sync failed: {e}")
                return {
                    "success": False,
                    "mode": "live_google_sheets",
                    "synced_count": 0,
                    "spreadsheet_id": target_sheet_id,
                    "error": str(e),
                }

        # Fallback / Demo Mode: write to CSV file mimicking the Google Sheet
        export_file = self._local_export_file()
        os.makedirs(os.path.dirname(export_file), exist_ok=True)

        existing_rows = {}
        output_headers = list(headers)
        if os.path.exists(export_file):
            with open(export_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                output_headers = list(reader.fieldnames or headers)
                output_headers.extend(header for header in headers if header not in output_headers)
                for row in reader:
                    existing_rows[str(row.get("ID", ""))] = row
        for influencer_id, row_data in rows.items():
            existing_rows.setdefault(str(influencer_id), {}).update(
                {key: str(value) for key, value in row_data.items()}
            )
        with open(export_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=output_headers)
            writer.writeheader()
            writer.writerows(existing_rows.values())

        logger.info(f"Upserted {len(rows)} influencers to local Google Sheets sync file: {export_file}")
        return {
            "success": True,
            "mode": "demo_synced_storage",
            "synced_count": len(rows),
            "local_path": export_file,
            "message": f"Saved {len(rows)} influencers to synced spreadsheet archive. (Configure GOOGLE_SPREADSHEET_ID and google_credentials.json to push directly to cloud Google Drive)."
        }

    @staticmethod
    def _column_label(column_number: int) -> str:
        label = ""
        while column_number:
            column_number, remainder = divmod(column_number - 1, 26)
            label = chr(65 + remainder) + label
        return label

    @staticmethod
    def _local_export_file() -> str:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        return os.path.join(data_dir, "google_sheets_synced_export.csv")

google_sheets_service = GoogleSheetsService()
