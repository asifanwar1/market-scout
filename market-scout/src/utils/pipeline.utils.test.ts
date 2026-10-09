import { describe, expect, it } from "vitest";

import type { TActivity } from "@/api/services/pipeline/pipeline.response.types";
import { CLOSING_STATUS } from "@/constants/pipeline.constants";
import {
    DUE_TONE,
    buildOutcomePayload,
    defaultDueStamp,
    describeActivity,
    describeDue,
    formatMoney,
    formatPercent,
    isAmountValid,
    isClosingStatus,
    parseAmount,
    percentOf,
    todayStamp,
    toDateStamp,
} from "./pipeline.utils";

const TODAY = "2026-10-08";

describe("describeDue", () => {
    it("says how late an overdue task is", () => {
        expect(describeDue("2026-10-07", TODAY)).toEqual({ label: "Overdue by 1 day", tone: DUE_TONE.OVERDUE });
        expect(describeDue("2026-10-01", TODAY)).toEqual({ label: "Overdue by 7 days", tone: DUE_TONE.OVERDUE });
    });

    it("recognises today and tomorrow", () => {
        expect(describeDue(TODAY, TODAY)).toEqual({ label: "Due today", tone: DUE_TONE.TODAY });
        expect(describeDue("2026-10-09", TODAY)).toEqual({ label: "Due tomorrow", tone: DUE_TONE.UPCOMING });
    });

    it("counts days across a month end", () => {
        expect(describeDue("2026-11-02", TODAY)).toEqual({ label: "Due in 25 days", tone: DUE_TONE.UPCOMING });
    });
});

describe("dates", () => {
    it("writes a local date as year-month-day", () => {
        expect(toDateStamp(new Date(2026, 0, 5))).toBe("2026-01-05");
        expect(todayStamp()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it("suggests a due date a few days away", () => {
        expect(describeDue(defaultDueStamp(), todayStamp()).tone).toBe(DUE_TONE.UPCOMING);
    });
});

describe("isClosingStatus", () => {
    it("is true only for customer and not interested", () => {
        expect(isClosingStatus("customer")).toBe(true);
        expect(isClosingStatus("not_interested")).toBe(true);
        expect(isClosingStatus("quoted")).toBe(false);
        expect(isClosingStatus("")).toBe(false);
    });
});

describe("parseAmount", () => {
    it("reads plain and comma-separated numbers", () => {
        expect(parseAmount("1500")).toBe(1500);
        expect(parseAmount(" 1,500.50 ")).toBe(1500.5);
        expect(parseAmount("0")).toBe(0);
    });

    it("treats blanks, text and negatives as no amount", () => {
        expect(parseAmount("")).toBeNull();
        expect(parseAmount("   ")).toBeNull();
        expect(parseAmount("lots")).toBeNull();
        expect(parseAmount("-5")).toBeNull();
        expect(parseAmount("Infinity")).toBeNull();
    });

    it("accepts a blank but not a bad amount in the form", () => {
        expect(isAmountValid("")).toBe(true);
        expect(isAmountValid("12")).toBe(true);
        expect(isAmountValid("abc")).toBe(false);
        expect(isAmountValid("-1")).toBe(false);
    });
});

describe("buildOutcomePayload", () => {
    const fields = { amount: " 2,000 ", product: "  Quote Pro ", reason: "price" as const, note: "  Annual plan " };

    it("sends the deal for a customer and not the loss reason", () => {
        expect(buildOutcomePayload(CLOSING_STATUS.WON, fields)).toEqual({ value: 2000, product: "Quote Pro", note: "Annual plan" });
    });

    it("sends only the reason for a lost lead and not the deal", () => {
        expect(buildOutcomePayload(CLOSING_STATUS.LOST, fields)).toEqual({ loss_reason: "price", note: "Annual plan" });
    });

    it("turns blanks into null so they clear the saved value", () => {
        const empty = { amount: "", product: " ", reason: "" as const, note: "" };

        expect(buildOutcomePayload(CLOSING_STATUS.WON, empty)).toEqual({ value: null, product: null, note: null });
        expect(buildOutcomePayload(CLOSING_STATUS.LOST, empty)).toEqual({ loss_reason: null, note: null });
    });
});

describe("formatting", () => {
    it("formats money in the given currency", () => {
        expect(formatMoney(1500, "USD")).toBe("$1,500.00");
        expect(formatMoney(1500, "PKR")).toContain("1,500");
    });

    it("falls back to the code when the currency is not a real one", () => {
        expect(formatMoney(1500, "$$")).toBe("$$ 1,500");
    });

    it("formats rates, with a dash when there is none", () => {
        expect(formatPercent(0.667)).toBe("67%");
        expect(formatPercent(1)).toBe("100%");
        expect(formatPercent(null)).toBe("—");
    });

    it("works out a share of the whole without dividing by zero", () => {
        expect(percentOf(1, 4)).toBe(25);
        expect(percentOf(3, 0)).toBe(0);
    });
});

describe("describeActivity", () => {
    const activity = (overrides: Partial<TActivity>): TActivity => ({
        id: 1,
        kind: "note",
        summary: null,
        from_value: null,
        to_value: null,
        created_by: null,
        created_at: "2026-10-08T10:00:00",
        ...overrides,
    });

    it("shows a status move with the status names people see", () => {
        expect(describeActivity(activity({ kind: "status_change", from_value: "not_interested", to_value: "meeting" }))).toEqual({
            title: "Status: Not interested → Meeting",
            detail: null,
        });
    });

    it("shows who a lead moved between", () => {
        expect(describeActivity(activity({ kind: "assignment", from_value: "Unassigned", to_value: "Sara" })).title).toBe("Assigned: Unassigned → Sara");
    });

    it("shows what the person wrote for a call or note", () => {
        expect(describeActivity(activity({ kind: "call", summary: "Wants a quote" }))).toEqual({ title: "Call", detail: "Wants a quote" });
        expect(describeActivity(activity({ kind: "whatsapp", summary: "Sent brochure" })).title).toBe("WhatsApp");
    });

    it("names the follow-up that was completed", () => {
        expect(describeActivity(activity({ kind: "task_completed", summary: "Send the quote" }))).toEqual({
            title: "Completed a follow-up",
            detail: "Send the quote",
        });
    });

    it("keeps an unknown status readable", () => {
        expect(describeActivity(activity({ kind: "status_change", from_value: "odd", to_value: null })).title).toBe("Status: odd → —");
    });
});

