import type { TListResponse } from "@/api/types/common";
import type { AlertKind } from "@/constants/alert.constants";

export type TAlert = {
    id: number;
    kind: AlertKind;
    message: string;
    detail: Record<string, unknown>;
    business_id: number;
    business_name: string;
    city: string | null;
    run_id: number | null;
    is_read: boolean;
    created_at: string;
};

export type TGetAlertsResponse = TListResponse<TAlert> & { unread: number };

export type TAlertSummary = {
    unread: number;
};

export type TAlertSettings = {
    new_lead_enabled: boolean;
    new_lead_min_score: number;
    growing_enabled: boolean;
    growing_min_new_reviews: number;
    growing_min_percent: number;
    reachable_enabled: boolean;
    max_per_run: number;
};
