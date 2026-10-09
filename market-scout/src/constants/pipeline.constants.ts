import { LEAD_STATUS } from "./lead-status.constants";

export const OUTCOME_KIND = {
    WON: "won",
    LOST: "lost",
} as const;

export type OutcomeKind = (typeof OUTCOME_KIND)[keyof typeof OUTCOME_KIND];

export const CLOSING_STATUS = {
    WON: LEAD_STATUS.CUSTOMER,
    LOST: LEAD_STATUS.NOT_INTERESTED,
} as const;

export type ClosingStatus = (typeof CLOSING_STATUS)[keyof typeof CLOSING_STATUS];

export const LOSS_REASON = {
    PRICE: "price",
    COMPETITOR: "competitor",
    NO_NEED: "no_need",
    NO_RESPONSE: "no_response",
    BAD_CONTACT_DATA: "bad_contact_data",
    WRONG_BUSINESS: "wrong_business",
    OTHER: "other",
} as const;

export type LossReason = (typeof LOSS_REASON)[keyof typeof LOSS_REASON];

export const LOSS_REASON_OPTIONS: ReadonlyArray<{ value: LossReason; label: string }> = [
    { value: LOSS_REASON.PRICE, label: "Price" },
    { value: LOSS_REASON.COMPETITOR, label: "Using a competitor" },
    { value: LOSS_REASON.NO_NEED, label: "No need" },
    { value: LOSS_REASON.NO_RESPONSE, label: "No response" },
    { value: LOSS_REASON.BAD_CONTACT_DATA, label: "Bad contact details" },
    { value: LOSS_REASON.WRONG_BUSINESS, label: "Wrong kind of business" },
    { value: LOSS_REASON.OTHER, label: "Other" },
];

export const NO_LOSS_REASON_LABEL = "Not recorded";

export const getLossReasonLabel = (value: string | null | undefined): string =>
    LOSS_REASON_OPTIONS.find((option) => option.value === value)?.label ?? NO_LOSS_REASON_LABEL;

export const ACTIVITY_KIND = {
    NOTE: "note",
    CALL: "call",
    WHATSAPP: "whatsapp",
    EMAIL: "email",
    MEETING: "meeting",
    STATUS_CHANGE: "status_change",
    ASSIGNMENT: "assignment",
    TASK_COMPLETED: "task_completed",
    OUTCOME_UPDATED: "outcome_updated",
} as const;

export type ActivityKind = (typeof ACTIVITY_KIND)[keyof typeof ACTIVITY_KIND];

export type ManualActivityKind =
    | typeof ACTIVITY_KIND.NOTE
    | typeof ACTIVITY_KIND.CALL
    | typeof ACTIVITY_KIND.WHATSAPP
    | typeof ACTIVITY_KIND.EMAIL
    | typeof ACTIVITY_KIND.MEETING;

export const MANUAL_ACTIVITY_OPTIONS: ReadonlyArray<{ value: ManualActivityKind; label: string }> = [
    { value: ACTIVITY_KIND.NOTE, label: "Note" },
    { value: ACTIVITY_KIND.CALL, label: "Call" },
    { value: ACTIVITY_KIND.WHATSAPP, label: "WhatsApp" },
    { value: ACTIVITY_KIND.EMAIL, label: "Email" },
    { value: ACTIVITY_KIND.MEETING, label: "Meeting" },
];

export const TASK_SCOPE = {
    OPEN: "open",
    OVERDUE: "overdue",
    TODAY: "today",
    UPCOMING: "upcoming",
    DONE: "done",
} as const;

export type TaskScope = (typeof TASK_SCOPE)[keyof typeof TASK_SCOPE];

export const TASK_SCOPE_OPTIONS: ReadonlyArray<{ value: TaskScope; label: string }> = [
    { value: TASK_SCOPE.OPEN, label: "All open" },
    { value: TASK_SCOPE.OVERDUE, label: "Overdue" },
    { value: TASK_SCOPE.TODAY, label: "Today" },
    { value: TASK_SCOPE.UPCOMING, label: "Upcoming" },
    { value: TASK_SCOPE.DONE, label: "Done" },
];

export const CONVERSION_GROUP = {
    SOURCE: "source",
    SEGMENT: "segment",
    CITY: "city",
} as const;

export type ConversionGroup = (typeof CONVERSION_GROUP)[keyof typeof CONVERSION_GROUP];

export const CONVERSION_GROUP_OPTIONS: ReadonlyArray<{ value: ConversionGroup; label: string }> = [
    { value: CONVERSION_GROUP.SOURCE, label: "By source" },
    { value: CONVERSION_GROUP.SEGMENT, label: "By segment" },
    { value: CONVERSION_GROUP.CITY, label: "By city" },
];

export const TASK_SUMMARY_REFETCH_MS = 60000;
export const DRAWER_LIST_LIMIT = 50;
export const DATE_INPUT_FORMAT = "yyyy-MM-dd";
export const DEFAULT_TASK_DUE_DAYS = 3;
