import type { AlertKind } from "@/constants/alert.constants";

export type TGetAlertsParams = {
    page?: number;
    limit?: number;
    unread_only?: boolean;
    kind?: AlertKind;
};

export type TMarkReadBody = {
    ids?: number[];
    all?: boolean;
};

export type TAlertSettingsBody = {
    new_lead_enabled?: boolean;
    new_lead_min_score?: number;
    growing_enabled?: boolean;
    growing_min_new_reviews?: number;
    growing_min_percent?: number;
    reachable_enabled?: boolean;
    max_per_run?: number;
};
