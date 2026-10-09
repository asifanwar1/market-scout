import type { TListResponse } from "@/api/types/common";
import type { ActivityKind, LossReason, OutcomeKind } from "@/constants/pipeline.constants";

export type TPerson = {
    id: number;
    full_name: string;
};

export type TOutcome = {
    kind: OutcomeKind;
    value: number | null;
    product: string | null;
    loss_reason: LossReason | null;
    note: string | null;
    closed_at: string;
    closed_by: TPerson | null;
};

export type TActivity = {
    id: number;
    kind: ActivityKind;
    summary: string | null;
    from_value: string | null;
    to_value: string | null;
    created_by: TPerson | null;
    created_at: string;
};

export type TActivityList = TListResponse<TActivity>;

export type TTask = {
    id: number;
    business_id: number;
    business_name: string;
    title: string;
    due_on: string;
    assigned_to: TPerson | null;
    completed_at: string | null;
    created_at: string;
};

export type TTaskList = TListResponse<TTask>;

export type TTaskSummary = {
    overdue: number;
    due_today: number;
    open: number;
};

export type TPipelineConfig = {
    deal_currency: string;
};
