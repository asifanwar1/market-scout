import type { ScheduleFrequency } from "@/constants/schedule.constants";

export type TGetSchedulesParams = {
    page?: number;
    limit?: number;
};

export type TCreateScheduleBody = {
    name: string;
    frequency: ScheduleFrequency;
    profile_id: number;
    geography_ids: number[];
    source_keys: string[];
    segment_slugs?: string[] | null;
    enrich_websites: boolean;
    max_paid_requests?: number | null;
};

export type TUpdateScheduleBody = {
    name?: string;
    frequency?: ScheduleFrequency;
    is_active?: boolean;
};
