export type TSheetsSettings = {
    has_credentials: boolean;
    credentials_source: "saved" | "environment" | null;
    credentials_needs_reentry: boolean;
    service_account_email: string | null;
    spreadsheet_id: string | null;
    spreadsheet_url: string | null;
    spreadsheet_title: string | null;
    worksheet_title: string;
    auto_sync: boolean;
    is_configured: boolean;
    is_syncing: boolean;
    last_synced_at: string | null;
    last_attempt_at: string | null;
    last_sync_ok: boolean | null;
    last_error: string | null;
    last_row_count: number | null;
};

export type TSheetsTestResponse = {
    ok: boolean;
    message: string;
};
