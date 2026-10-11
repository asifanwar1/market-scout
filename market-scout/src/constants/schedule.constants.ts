export const SCHEDULE_FREQUENCY = {
    DAILY: "daily",
    WEEKLY: "weekly",
    MONTHLY: "monthly",
} as const;

export type ScheduleFrequency = (typeof SCHEDULE_FREQUENCY)[keyof typeof SCHEDULE_FREQUENCY];

export const SCHEDULE_FREQUENCY_OPTIONS: ReadonlyArray<{ value: ScheduleFrequency; label: string }> = [
    { value: SCHEDULE_FREQUENCY.DAILY, label: "Every day" },
    { value: SCHEDULE_FREQUENCY.WEEKLY, label: "Every week" },
    { value: SCHEDULE_FREQUENCY.MONTHLY, label: "Every month" },
];

export const getScheduleFrequencyLabel = (value: string): string =>
    SCHEDULE_FREQUENCY_OPTIONS.find((option) => option.value === value)?.label ?? value;

export const REPEAT_URL_PARAM = "repeat";
export const REPEAT_URL_VALUE = "1";

export const JOB_KIND_LABELS: Record<string, string> = {
    run: "Runs",
    import: "Imports",
    ai_batch: "AI batches",
    quality: "Data checks",
    webhook: "Webhook deliveries",
};
