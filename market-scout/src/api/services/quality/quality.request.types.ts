export type TCheckBody = {
    business_ids: number[];
    refresh?: boolean;
};

export type TGetDuplicatesParams = {
    page?: number;
    limit?: number;
    status?: string;
};

export type TMergeBody = {
    keep_id: number;
};

export type TScoringProfileBody = {
    profile_id: number;
};

export type TQualitySettingsBody = {
    check_after_runs?: boolean;
    max_checks_per_run?: number;
};
