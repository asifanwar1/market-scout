export const ALERT_KIND = {
    NEW_LEAD: "new_lead",
    GROWING: "growing",
    REACHABLE: "reachable",
} as const;

export type AlertKind = (typeof ALERT_KIND)[keyof typeof ALERT_KIND];

export const ALERT_KIND_OPTIONS: ReadonlyArray<{ value: AlertKind; label: string }> = [
    { value: ALERT_KIND.NEW_LEAD, label: "New leads" },
    { value: ALERT_KIND.GROWING, label: "Growing businesses" },
    { value: ALERT_KIND.REACHABLE, label: "Newly reachable" },
];

export const getAlertKindLabel = (value: string): string =>
    ALERT_KIND_OPTIONS.find((option) => option.value === value)?.label ?? value;

export const ALERT_SETTING_LIMITS = {
    SCORE: { min: 0, max: 100 },
    NEW_REVIEWS: { min: 1, max: 10000 },
    PERCENT: { min: 0, max: 1000 },
    PER_RUN: { min: 1, max: 500 },
} as const;
