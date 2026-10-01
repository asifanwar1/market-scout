import type {
    TMatchRules,
    TOsmFilter,
    TScoringConfig,
} from "./profiles.response.types";

export type TGetProfilesParams = {
    page?: number;
    limit?: number;
    search?: string;
    is_active?: boolean;
};

export type TSegmentInput = {
    id?: number;
    name: string;
    slug: string;
    description?: string | null;
    match_rules: TMatchRules;
    sort_order: number;
};

export type TSearchTermInput = {
    id?: number;
    text: string;
    segment_slug: string;
    osm_filter: TOsmFilter | null;
    language: "en" | "ur-roman";
    is_active: boolean;
};

export type TProfileBody = {
    name: string;
    description?: string | null;
    is_active: boolean;
    scoring_config: TScoringConfig;
    segments: TSegmentInput[];
    search_terms: TSearchTermInput[];
};
