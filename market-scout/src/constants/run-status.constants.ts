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
    { value: "queued", label: "Queued", className: "bg-muted text-muted-foreground" },
    { value: "running", label: "Running", className: "bg-info text-info-foreground" },
    { value: "cancelling", label: "Cancelling", className: "bg-warning text-warning-foreground" },
    { value: "completed", label: "Completed", className: "bg-success text-success-foreground" },
    { value: "failed", label: "Failed", className: "bg-destructive/10 text-destructive" },
    { value: "cancelled", label: "Cancelled", className: "bg-muted text-muted-foreground" },
];

export const getRunStatus = (value: string) =>
    RUN_STATUS_OPTIONS.find((option) => option.value === value);

export const TASK_STATUS_OPTIONS: Record<string, { label: string; className: string }> = {
    pending: { label: "Pending", className: "bg-muted text-muted-foreground" },
    running: { label: "Running", className: "bg-info text-info-foreground" },
    done: { label: "Done", className: "bg-success text-success-foreground" },
    failed: { label: "Failed", className: "bg-destructive/10 text-destructive" },
    skipped: { label: "Skipped", className: "bg-warning text-warning-foreground" },
};
