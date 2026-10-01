import type { TListResponse } from "@/api/types/common";

export type TProfileListItem = {
    id: number;
    name: string;
    slug: string;
    description: string | null;
    is_active: boolean;
    segment_count: number;
    term_count: number;
    created_at: string;
};

export type TGetProfilesResponse = TListResponse<TProfileListItem>;

export type TOsmFilter = {
    clauses: string[][];
};

export type TMatchRules = {
    name_patterns: string[];
};

export type TScoringConfig = {
    has_phone: number;
    has_whatsapp_likely: number;
    has_website: number;
    has_email: number;
    has_reviews: number;
    name_matches_segment: number;
};

export type TSegment = {
    id: number;
    name: string;
    slug: string;
    description: string | null;
    match_rules: TMatchRules;
    sort_order: number;
};

export type TSearchTerm = {
    id: number;
    text: string;
    segment_id: number;
    segment_slug: string;
    osm_filter: TOsmFilter | null;
    language: "en" | "ur-roman";
    is_active: boolean;
};

export type TProfileDetail = TProfileListItem & {
    scoring_config: TScoringConfig;
    segments: TSegment[];
    search_terms: TSearchTerm[];
    updated_at: string | null;
};
