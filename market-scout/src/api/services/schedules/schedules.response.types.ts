import type { TListResponse } from "@/api/types/common";
import type { RunStatus } from "@/constants/run-status.constants";
import type { ScheduleFrequency } from "@/constants/schedule.constants";

export type TScheduleLastRun = {
    id: number;
    status: RunStatus;
    new_leads: number;
    started_at: string | null;
    finished_at: string | null;
};

export type TSchedule = {
    id: number;
    name: string;
    profile_id: number | null;
    profile_name: string;
    is_active: boolean;
    frequency: ScheduleFrequency;
    geography_ids: number[];
    cities: string[];
    source_keys: string[];
    segment_slugs: string[] | null;
    enrich_websites: boolean;
    max_paid_requests: number | null;
    next_run_at: string;
    last_run_at: string | null;
    last_run: TScheduleLastRun | null;
    consecutive_failures: number;
    last_error: string | null;
    created_at: string;
};

export type TGetSchedulesResponse = TListResponse<TSchedule>;
