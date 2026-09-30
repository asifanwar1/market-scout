import type { TListResponse } from "@/api/types/common";
import type { RunStatus } from "@/constants/run-status.constants";

export type TRunSourceStats = Record<string, number>;

export type TRun = {
    id: number;
    profile_id: number | null;
    profile_name: string;
    created_by_id: number | null;
    status: RunStatus;
    source_keys: string[];
    segment_slugs: string[] | null;
    enrich_websites: boolean;
    refresh: boolean;
    max_paid_requests: number | null;
    paid_requests_used: number;
    estimated_cost_usd: number;
    tasks_total: number;
    tasks_done: number;
    tasks_failed: number;
    tasks_skipped: number;
    progress_percent: number;
    enrich_total: number;
    enrich_done: number;
    stats: Record<string, TRunSourceStats>;
    error: string | null;
    created_at: string;
    started_at: string | null;
    finished_at: string | null;
};

export type TGetRunsResponse = TListResponse<TRun>;

export type TRunTask = {
    id: number;
    source_key: string;
    geography_id: number | null;
    geography_name: string;
    term_text: string;
    term_language: string;
    segment_slug: string;
    status: "pending" | "running" | "done" | "failed" | "skipped";
    results_count: number;
    new_count: number;
    requests_made: number;
    error: string | null;
    started_at: string | null;
    finished_at: string | null;
};

export type TGetRunTasksResponse = TListResponse<TRunTask>;

export type TSourceEstimate = {
    source_key: string;
    name: string;
    is_paid: boolean;
    tasks: number;
    tasks_skipped: number;
    max_requests: number | null;
    estimated_cost_usd: number | null;
};

export type TRunEstimate = {
    profile_name: string;
    cities: number;
    tasks_total: number;
    tasks_to_run: number;
    tasks_skipped: number;
    by_source: TSourceEstimate[];
    paid_requests_max: number;
    estimated_cost_usd: number;
    estimated_minutes: number;
    allowed: boolean;
    warnings: string[];
};
