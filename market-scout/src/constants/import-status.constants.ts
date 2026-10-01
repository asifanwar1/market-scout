import type { TImportStatus } from "@/api/services/imports/imports.response.types";

export const IMPORT_STATUS = {
    QUEUED: "queued",
    RUNNING: "running",
    CANCELLING: "cancelling",
    COMPLETED: "completed",
    FAILED: "failed",
    CANCELLED: "cancelled",
} as const;

export const IMPORT_STATUS_OPTIONS: ReadonlyArray<{ value: TImportStatus; label: string; className: string }> = [
    { value: IMPORT_STATUS.QUEUED, label: "Queued", className: "bg-muted text-muted-foreground" },
    { value: IMPORT_STATUS.RUNNING, label: "Importing", className: "bg-info text-info-foreground" },
    { value: IMPORT_STATUS.CANCELLING, label: "Cancelling", className: "bg-warning text-warning-foreground" },
    { value: IMPORT_STATUS.COMPLETED, label: "Completed", className: "bg-success text-success-foreground" },
    { value: IMPORT_STATUS.FAILED, label: "Failed", className: "bg-destructive/10 text-destructive" },
    { value: IMPORT_STATUS.CANCELLED, label: "Cancelled", className: "bg-muted text-muted-foreground" },
];

export const ACTIVE_IMPORT_STATUSES: ReadonlyArray<TImportStatus> = [IMPORT_STATUS.QUEUED, IMPORT_STATUS.RUNNING, IMPORT_STATUS.CANCELLING];

export const getImportStatus = (value: string) => IMPORT_STATUS_OPTIONS.find((option) => option.value === value);

export const SKIP_REASON_LABELS: Record<string, string> = {
    no_name: "had no name",
    no_contact: "had no phone, email or website",
};
