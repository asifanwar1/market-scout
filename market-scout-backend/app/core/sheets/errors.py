class SheetsError(Exception):
    """Something went wrong talking to Google Sheets. The message is safe to show to a person."""


class SheetsAuthError(SheetsError):
    """Google refused the service-account key itself."""
