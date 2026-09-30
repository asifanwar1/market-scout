import type { LeadStatus } from "@/constants/lead-status.constants";

export type TBusinessSort = "score" | "newest" | "last_seen" | "name";
export type TSortDirection = "asc" | "desc";

export type TBusinessFilters = {
    profile_id?: number;
    segment?: string;
    // A city, or a province / the country for every city inside.
    geography_id?: number;
    has_phone?: boolean;
    whatsapp_likely?: boolean;
    has_email?: boolean;
    has_website?: boolean;
    status?: LeadStatus;
    assigned_to_id?: number;
    unassigned?: boolean;
    source?: string;
    min_score?: number;
    search?: string;
};

export type TGetBusinessesParams = TBusinessFilters & {
    page?: number;
    limit?: number;
    sort?: TBusinessSort;
    direction?: TSortDirection;
};

export type TUpdateBusinessBody = {
    lead_status?: LeadStatus;
    notes?: string | null;
    assigned_to_id?: number | null;
};

export type TBulkUpdateBody = {
    business_ids: number[];
    lead_status?: LeadStatus;
    assigned_to_id?: number | null;
};

export type TDoNotContactBody = {
    reason?: string | null;
};
