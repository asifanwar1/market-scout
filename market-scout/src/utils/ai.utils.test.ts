import { describe, expect, it } from "vitest";

import type { TAiBatch } from "@/api/services/ai/ai.response.types";
import { batchProgress, describeBatch, formatAiCost, getAiModelLabel } from "./ai.utils";

const batch = (overrides: Partial<TAiBatch>): TAiBatch => ({
    id: 1,
    status: "completed",
    total: 10,
    done: 10,
    analyzed: 0,
    skipped: 0,
    declined: 0,
    failed: 0,
    spent_usd: 0,
    error: null,
    error_samples: [],
    created_at: "2026-10-09T10:00:00",
    finished_at: null,
    ...overrides,
});

describe("formatAiCost", () => {
    it("keeps three decimals for amounts under a dollar so small costs are visible", () => {
        expect(formatAiCost(0.054)).toBe("$0.054");
        expect(formatAiCost(0.0049)).toBe("$0.005");
        expect(formatAiCost(0)).toBe("$0.000");
    });

    it("uses cents for a dollar or more", () => {
        expect(formatAiCost(1)).toBe("$1.00");
        expect(formatAiCost(1234.5)).toBe("$1,234.50");
    });
});

describe("getAiModelLabel", () => {
    it("shows the name people know and falls back to the raw id", () => {
        expect(getAiModelLabel("claude-opus-5-5")).toBe("Claude Opus 5.5");
        expect(getAiModelLabel("claude-future-9")).toBe("claude-future-9");
        expect(getAiModelLabel(null)).toBe("an AI model");
    });
});

describe("describeBatch", () => {
    it("lists only the outcomes that happened", () => {
        expect(describeBatch(batch({ analyzed: 7, skipped: 2, failed: 1 }))).toEqual(["7 analysed", "2 skipped", "1 failed"]);
        expect(describeBatch(batch({ declined: 1 }))).toEqual(["1 declined by the AI"]);
    });

    it("says nothing when nothing happened", () => {
        expect(describeBatch(batch({}))).toEqual([]);
    });
});

describe("batchProgress", () => {
    it("is the share of leads handled so far", () => {
        expect(batchProgress(batch({ total: 8, done: 2 }))).toBe(25);
        expect(batchProgress(batch({ total: 0, done: 0 }))).toBe(0);
    });
});
