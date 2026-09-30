export type TUpdateSourceBody = {
    is_enabled?: boolean;
    // A new key to save (stored encrypted, never shown again).
    api_key?: string;
    clear_api_key?: boolean;
};
