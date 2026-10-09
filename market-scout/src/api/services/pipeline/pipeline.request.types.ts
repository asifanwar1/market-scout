import type { LossReason, ManualActivityKind, TaskScope } from "@/constants/pipeline.constants";

export type TOutcomeInput = {
    value?: number | null;
    product?: string | null;
    loss_reason?: LossReason | null;
    note?: string | null;
};

export type TActivityBody = {
    kind: ManualActivityKind;
    summary: string;
};

export type TTaskBody = {
    title: string;
    due_on: string;
    assigned_to_id?: number | null;
};

export type TTaskUpdateBody = {
    title?: string;
    due_on?: string;
    assigned_to_id?: number | null;
    done?: boolean;
};

export type TActivityParams = {
    page?: number;
    limit?: number;
};

export type TGetTasksParams = {
    scope?: TaskScope;
    mine?: boolean;
    business_id?: number;
    today?: string;
    page?: number;
    limit?: number;
};

export type TTaskSummaryParams = {
    mine?: boolean;
    today?: string;
};
