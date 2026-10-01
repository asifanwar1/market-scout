export type TUpdateSheetsBody = {
    // The sheet's link or bare ID; an empty string disconnects it.
    spreadsheet?: string;
    auto_sync?: boolean;
    // The whole downloaded service-account JSON (stored encrypted, never shown again).
    credentials_json?: string;
    clear_credentials?: boolean;
};
