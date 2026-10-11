export const CHECK_STATUS = {
    OK: "ok",
    BAD: "bad",
    WARNING: "warning",
} as const;

export const WEBSITE_STATUS = {
    OK: "ok",
    DEAD: "dead",
} as const;

export const QUALITY_TASK_STATUS = {
    QUEUED: "queued",
    RUNNING: "running",
    COMPLETED: "completed",
    FAILED: "failed",
} as const;

export type QualityTaskStatus = (typeof QUALITY_TASK_STATUS)[keyof typeof QUALITY_TASK_STATUS];

export const ACTIVE_QUALITY_TASK_STATUSES: ReadonlyArray<QualityTaskStatus> = [
    QUALITY_TASK_STATUS.QUEUED,
    QUALITY_TASK_STATUS.RUNNING,
];

export const DUPLICATE_CONFIDENCE = {
    LIKELY: "likely",
    POSSIBLE: "possible",
} as const;

export type DuplicateConfidence = (typeof DUPLICATE_CONFIDENCE)[keyof typeof DUPLICATE_CONFIDENCE];

export const DUPLICATE_REASON_LABELS: Record<string, string> = {
    phone: "Share a phone number",
    location: "Close together with a similar name",
    website: "Share a website",
};

export const CHECK_COUNT_LABELS: ReadonlyArray<{ key: string; singular: string; plural: string }> = [
    { key: "emails_ok", singular: "email works", plural: "emails work" },
    { key: "emails_bad", singular: "email cannot receive mail", plural: "emails cannot receive mail" },
    { key: "emails_unknown", singular: "email could not be checked", plural: "emails could not be checked" },
    { key: "websites_ok", singular: "website answers", plural: "websites answer" },
    { key: "websites_dead", singular: "website is down", plural: "websites are down" },
    { key: "websites_unknown", singular: "website could not be checked", plural: "websites could not be checked" },
    { key: "phones_shared", singular: "phone number is shared", plural: "phone numbers are shared" },
    { key: "skipped", singular: "lead had nothing to check", plural: "leads had nothing to check" },
];

export const QUALITY_SETTING_LIMITS = {
    PER_RUN: { min: 1, max: 2000 },
} as const;
