import type { TListResponse } from "@/api/types/common";
import type { DuplicateConfidence, QualityTaskStatus } from "@/constants/quality.constants";

export type TQualityTask = {
    id: number;
    kind: "contact_check" | "duplicate_scan";
    status: QualityTaskStatus;
    total: number;
    done: number;
    counts: Record<string, number>;
    error: string | null;
    created_at: string;
    started_at: string | null;
    finished_at: string | null;
};

export type TDuplicateSide = {
    id: number;
    name: string;
    address: string | null;
    city: string | null;
    website: string | null;
    phones: string[];
    emails: string[];
    score: number | null;
    lead_status: string;
    sources: string[];
    rating: number | null;
    review_count: number | null;
    assigned_to: string | null;
};

export type TDuplicate = {
    id: number;
    reason: string;
    similarity: number;
    confidence: DuplicateConfidence;
    status: string;
    created_at: string;
    a: TDuplicateSide;
    b: TDuplicateSide;
};

export type TGetDuplicatesResponse = TListResponse<TDuplicate>;

export type TMergeResponse = {
    kept_id: number;
    removed_id: number;
};

export type TScoringTrait = {
    key: string;
    label: string;
    with_count: number;
    with_wins: number;
    without_count: number;
    without_wins: number;
    win_rate_with: number | null;
    win_rate_without: number | null;
    difference: number | null;
    significant: boolean;
    current_weight: number;
    suggested_weight: number;
    note: string;
};

export type TScoring = {
    profile_id: number;
    profile_name: string;
    closed: number;
    won: number;
    lost: number;
    needed: number;
    enough_data: boolean;
    traits: TScoringTrait[];
    can_apply: boolean;
    can_revert: boolean;
};

export type TScoringApplyResponse = {
    weights: Record<string, number>;
    rescored: number;
};

export type TQualitySettings = {
    check_after_runs: boolean;
    max_checks_per_run: number;
};
