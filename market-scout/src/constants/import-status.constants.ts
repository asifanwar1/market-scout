import type { TImportStatus } from "@/api/services/imports/imports.response.types";

export const IMPORT_STATUS_OPTIONS: ReadonlyArray<{ value: TImportStatus; label: string; className: string }> = [
    { value: "queued", label: "Queued", className: "bg-muted text-muted-foreground" },
    { value: "running", label: "Importing", className: "bg-info text-info-foreground" },
    { value: "cancelling", label: "Cancelling", className: "bg-warning text-warning-foreground" },
    { value: "completed", label: "Completed", className: "bg-success text-success-foreground" },
    { value: "failed", label: "Failed", className: "bg-destructive/10 text-destructive" },
    { value: "cancelled", label: "Cancelled", className: "bg-muted text-muted-foreground" },
];

export const ACTIVE_IMPORT_STATUSES: ReadonlyArray<TImportStatus> = ["queued", "running", "cancelling"];

export const getImportStatus = (value: string) => IMPORT_STATUS_OPTIONS.find((option) => option.value === value);

/** Plain-language reasons rows were set aside before importing. */
export const SKIP_REASON_LABELS: Record<string, string> = {
    no_name: "had no name",
    no_contact: "had no phone, email or website",
};
