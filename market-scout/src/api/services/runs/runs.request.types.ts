import type { RunStatus } from "@/constants/run-status.constants";

export type TGetRunsParams = {
    page?: number;
    limit?: number;
    status?: RunStatus;
};

export type TGetRunTasksParams = {
    page?: number;
    limit?: number;
    status?: string;
};

export type TCreateRunBody = {
    profile_id: number;
    geography_ids: number[];
    source_keys: string[];
    segment_slugs?: string[] | null;
    enrich_websites: boolean;
    refresh: boolean;
    max_paid_requests?: number | null;
};
