export const AI_ANALYSIS_STATUS = {
    OK: "ok",
    NO_TEXT: "no_text",
    DECLINED: "declined",
    FAILED: "failed",
} as const;

export type AiAnalysisStatus = (typeof AI_ANALYSIS_STATUS)[keyof typeof AI_ANALYSIS_STATUS];

export const AI_BATCH_STATUS = {
    QUEUED: "queued",
    RUNNING: "running",
    COMPLETED: "completed",
    STOPPED: "stopped",
    FAILED: "failed",
} as const;

export type AiBatchStatus = (typeof AI_BATCH_STATUS)[keyof typeof AI_BATCH_STATUS];

export const ACTIVE_AI_BATCH_STATUSES: ReadonlyArray<AiBatchStatus> = [AI_BATCH_STATUS.QUEUED, AI_BATCH_STATUS.RUNNING];

export const CONFIDENCE_LABELS: Record<string, string> = {
    low: "Low confidence",
    medium: "Medium confidence",
    high: "High confidence",
};

export const AI_MODEL_LABELS: Record<string, string> = {
    "claude-opus-5-5": "Claude Opus 5.5",
    "claude-sonnet-5-5": "Claude Sonnet 5.5",
    "claude-haiku-4-5": "Claude Haiku 4.5",
};

export const MIN_AI_FITS: ReadonlyArray<{ value: string; label: string }> = [
    { value: "50", label: "50+ (possible fit)" },
    { value: "70", label: "70+ (good fit)" },
    { value: "85", label: "85+ (strong fit)" },
];

export const AI_FIT_TITLE = "AI fit: how closely the AI thinks this business matches your ideal customer";
export const AI_ESTIMATE_DIGITS = 2;
export const AI_API_KEY_MIN_LENGTH = 8;
export const AI_BUDGET_MAX = 100000;
export const SHOWN_ERROR_SAMPLES = 5;
