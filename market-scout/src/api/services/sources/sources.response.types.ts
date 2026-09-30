import type { TListResponse } from "@/api/types/common";

export type TSource = {
    key: string;
    name: string;
    description: string;
    kind: "discovery" | "enrichment";
    requires_api_key: boolean;
    is_paid: boolean;
    is_enabled: boolean;
    has_key: boolean;
    key_hint: string | null;
    key_source: "saved" | "environment" | null;
    key_needs_reentry: boolean;
    is_available: boolean;
};

export type TGetSourcesResponse = TListResponse<TSource>;

export type TSourceTestResponse = {
    ok: boolean;
    message: string;
};
