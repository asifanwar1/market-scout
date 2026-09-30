import type { LeadStatus } from "@/constants/lead-status.constants";
import type { TListResponse } from "@/api/types/common";

export type TAssignedUser = {
    id: number;
    full_name: string;
};

export type TBusinessListItem = {
    id: number;
    name: string;
    address: string | null;
    city: string | null;
    province: string | null;
    profile_id: number | null;
    segment_slug: string | null;
    segment_name: string | null;
    score: number | null;
    lead_status: LeadStatus;
    assigned_to: TAssignedUser | null;
    primary_phone: string | null;
    whatsapp_likely: boolean;
    email: string | null;
    website: string | null;
    rating: number | null;
    review_count: number | null;
    sources: string[];
    first_seen_at: string;
    last_seen_at: string;
};

export type TGetBusinessesResponse = TListResponse<TBusinessListItem>;

export type TContactKind =
    | "phone"
    | "email"
    | "whatsapp"
    | "facebook"
    | "instagram";

export type TContactPoint = {
    id: number;
    kind: TContactKind;
    value: string;
    is_mobile: boolean;
    whatsapp_likely: boolean;
    source_key: string;
    created_at: string | null;
};

export type TClassification = {
    profile_id: number;
    segment_slug: string | null;
    segment_name: string | null;
    score: number;
};

export type TSourceRecord = {
    source_key: string;
    external_id: string;
    run_id: number | null;
    fetched_at: string;
};

export type TBusinessDetail = {
    id: number;
    name: string;
    address: string | null;
    city_id: number | null;
    city: string | null;
    province: string | null;
    latitude: number | null;
    longitude: number | null;
    website: string | null;
    rating: number | null;
    review_count: number | null;
    categories: string[];
    lead_status: LeadStatus;
    assigned_to: TAssignedUser | null;
    notes: string | null;
    classifications: TClassification[];
    contacts: TContactPoint[];
    sources: TSourceRecord[];
    first_seen_at: string;
    last_seen_at: string;
    enriched_at: string | null;
    updated_at: string | null;
};

export type TBulkUpdateResponse = {
    updated: number;
};

export type TDoNotContactResponse = {
    id: number;
    kind: "business" | "phone" | "email";
    value: string;
    business_id: number | null;
    identifiers: string[];
    reason: string | null;
    added_by_id: number | null;
    created_at: string;
};
