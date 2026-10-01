export const RUN_STATUS = {
    QUEUED: "queued",
    RUNNING: "running",
    CANCELLING: "cancelling",
    COMPLETED: "completed",
    FAILED: "failed",
    CANCELLED: "cancelled",
} as const;

export type RunStatus = (typeof RUN_STATUS)[keyof typeof RUN_STATUS];

export const ACTIVE_RUN_STATUSES: ReadonlyArray<RunStatus> = [
    RUN_STATUS.QUEUED,
    RUN_STATUS.RUNNING,
    RUN_STATUS.CANCELLING,
];

export const RUN_STATUS_OPTIONS: ReadonlyArray<{
    value: RunStatus;
    label: string;
    className: string;
}> = [
    { value: RUN_STATUS.QUEUED, label: "Queued", className: "bg-muted text-muted-foreground" },
    { value: RUN_STATUS.RUNNING, label: "Running", className: "bg-info text-info-foreground" },
    { value: RUN_STATUS.CANCELLING, label: "Cancelling", className: "bg-warning text-warning-foreground" },
    { value: RUN_STATUS.COMPLETED, label: "Completed", className: "bg-success text-success-foreground" },
    { value: RUN_STATUS.FAILED, label: "Failed", className: "bg-destructive/10 text-destructive" },
    { value: RUN_STATUS.CANCELLED, label: "Cancelled", className: "bg-muted text-muted-foreground" },
];

export const getRunStatus = (value: string) =>
    RUN_STATUS_OPTIONS.find((option) => option.value === value);

export const TASK_STATUS = {
    PENDING: "pending",
    RUNNING: "running",
    DONE: "done",
    FAILED: "failed",
    SKIPPED: "skipped",
} as const;

export const TASK_STATUS_OPTIONS: Record<string, { label: string; className: string }> = {
    [TASK_STATUS.PENDING]: { label: "Pending", className: "bg-muted text-muted-foreground" },
    [TASK_STATUS.RUNNING]: { label: "Running", className: "bg-info text-info-foreground" },
    [TASK_STATUS.DONE]: { label: "Done", className: "bg-success text-success-foreground" },
    [TASK_STATUS.FAILED]: { label: "Failed", className: "bg-destructive/10 text-destructive" },
    [TASK_STATUS.SKIPPED]: { label: "Skipped", className: "bg-warning text-warning-foreground" },
};
