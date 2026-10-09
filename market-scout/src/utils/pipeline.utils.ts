import { addDays, differenceInCalendarDays, format, parseISO } from "date-fns";

import type { TOutcomeInput } from "@/api/services/pipeline/pipeline.request.types";
import type { TActivity } from "@/api/services/pipeline/pipeline.response.types";
import { getLeadStatus } from "@/constants/lead-status.constants";
import {
    ACTIVITY_KIND,
    CLOSING_STATUS,
    MANUAL_ACTIVITY_OPTIONS,
    DATE_INPUT_FORMAT,
    DEFAULT_TASK_DUE_DAYS,
    type ClosingStatus,
    type LossReason,
} from "@/constants/pipeline.constants";
import { formatCount, pluralize } from "./format.utils";

export const DUE_TONE = {
    OVERDUE: "overdue",
    TODAY: "today",
    UPCOMING: "upcoming",
} as const;

export type DueTone = (typeof DUE_TONE)[keyof typeof DUE_TONE];

export type TDue = {
    label: string;
    tone: DueTone;
};

export type TOutcomeFields = {
    amount: string;
    product: string;
    reason: LossReason | "";
    note: string;
};

const NO_VALUE = "—";
const PERCENT_FACTOR = 100;
const THOUSANDS_SEPARATOR = /,/g;

export const isClosingStatus = (value: string): value is ClosingStatus =>
    value === CLOSING_STATUS.WON || value === CLOSING_STATUS.LOST;

export const toDateStamp =(date: Date): string => format(date, DATE_INPUT_FORMAT);

export const todayStamp = (): string => toDateStamp(new Date());

export const defaultDueStamp = (): string => toDateStamp(addDays(new Date(), DEFAULT_TASK_DUE_DAYS));

export const describeDue = (dueOn: string, today: string): TDue => {
    const days = differenceInCalendarDays(parseISO(dueOn), parseISO(today));
    if (days < 0) return { label: `Overdue by ${pluralize(-days, "day", "days")}`, tone: DUE_TONE.OVERDUE };
    if (days === 0) return { label: "Due today", tone: DUE_TONE.TODAY };
    if (days === 1) return { label: "Due tomorrow", tone: DUE_TONE.UPCOMING };
    return { label: `Due in ${days} days`, tone: DUE_TONE.UPCOMING };
};

export const parseAmount = (text: string): number | null => {
    const cleaned = text.replace(THOUSANDS_SEPARATOR, "").trim();
    if (cleaned === "") return null;
    const value = Number(cleaned);
    return Number.isFinite(value) && value >= 0 ? value : null;
};

export const isAmountValid = (text: string): boolean => text.trim() === "" || parseAmount(text) !== null;

export const buildOutcomePayload = (status: ClosingStatus, fields: TOutcomeFields): TOutcomeInput => {
    const note = fields.note.trim() || null;
    if (status === CLOSING_STATUS.WON) {
        return { value: parseAmount(fields.amount), product: fields.product.trim() || null, note };
    }
    return { loss_reason: fields.reason || null, note };
};

export type TActivityView = {
    title: string;
    detail: string | null;
};

const statusLabel = (value: string | null): string => (value ? (getLeadStatus(value)?.label ?? value) : NO_VALUE);

export const describeActivity = (activity: TActivity): TActivityView => {
    switch (activity.kind) {
        case ACTIVITY_KIND.STATUS_CHANGE:
            return { title: `Status: ${statusLabel(activity.from_value)} → ${statusLabel(activity.to_value)}`, detail: null };
        case ACTIVITY_KIND.ASSIGNMENT:
            return { title: `Assigned: ${activity.from_value ?? NO_VALUE} → ${activity.to_value ?? NO_VALUE}`, detail: null };
        case ACTIVITY_KIND.TASK_COMPLETED:
            return { title: "Completed a follow-up", detail: activity.summary };
        case ACTIVITY_KIND.OUTCOME_UPDATED:
            return { title: "Deal details updated", detail: null };
        default:
            return {
                title: MANUAL_ACTIVITY_OPTIONS.find((option) => option.value === activity.kind)?.label ?? activity.kind,
                detail: activity.summary,
            };
    }
};

export const formatMoney = (value: number, currency: string): string => {
    try {
        return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
    } catch {
        return `${currency} ${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value)}`;
    }
};

export const formatPercent = (value: number | null): string =>
    value === null ? NO_VALUE : `${formatCount(Math.round(value * PERCENT_FACTOR))}%`;

export const percentOf = (part: number, whole: number): number =>
    whole === 0 ? 0 : Math.round((part / whole) * PERCENT_FACTOR);
