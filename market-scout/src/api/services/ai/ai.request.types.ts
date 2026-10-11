export type TAiSettingsBody = {
    is_enabled?: boolean;
    api_key?: string;
    clear_api_key?: boolean;
    model?: string;
    monthly_budget_usd?: number;
};

export type TAiEstimateBody = {
    business_ids: number[];
    profile_id: number;
    refresh?: boolean;
};

export type TApplySegmentBody = {
    profile_id: number;
};
