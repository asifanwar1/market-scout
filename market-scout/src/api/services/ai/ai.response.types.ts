import type { AiAnalysisStatus, AiBatchStatus } from "@/constants/ai.constants";

export type TAiModel = {
    id: string;
    label: string;
    input_per_mtok_usd: number;
    output_per_mtok_usd: number;
};

export type TAiSettings = {
    is_enabled: boolean;
    has_key: boolean;
    key_hint: string | null;
    key_source: "saved" | "environment" | null;
    key_needs_reentry: boolean;
    model: string;
    models: TAiModel[];
    monthly_budget_usd: number;
    spent_this_month_usd: number;
    remaining_usd: number;
    analyses_this_month: number;
};

export type TAiTestResponse = {
    ok: boolean;
    message: string;
};

export type TAiStatus = {
    is_ready: boolean;
    reason: string | null;
    model_label: string | null;
    remaining_usd: number;
};

export type TAiEstimate = {
    leads: number;
    to_analyze: number;
    without_website: number;
    already_analyzed: number;
    estimated_cost_usd: number;
    remaining_usd: number;
    within_budget: boolean;
    model_label: string;
    warnings: string[];
};

export type TAiBatch = {
    id: number;
    status: AiBatchStatus;
    total: number;
    done: number;
    analyzed: number;
    skipped: number;
    declined: number;
    failed: number;
    spent_usd: number;
    error: string | null;
    error_samples: string[];
    created_at: string;
    finished_at: string | null;
};

export type TAiResult = {
    profile_id: number;
    status: AiAnalysisStatus;
    summary: string | null;
    segment_slug: string | null;
    segment_name: string | null;
    segment_reason: string | null;
    current_segment_slug: string | null;
    fit_score: number | null;
    fit_reason: string | null;
    confidence: string | null;
    model: string | null;
    pages_read: number;
    truncated: boolean;
    error: string | null;
    analyzed_at: string;
};
