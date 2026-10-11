import { describe, expect, it } from "vitest";

import type { TScoringTrait } from "@/api/services/quality/quality.response.types";
import { describeCheckCounts, describeTrait, formatRate, weightChange } from "./quality.utils";

const TRAIT: TScoringTrait = {
    key: "has_email",
    label: "Has a working email",
    with_count: 20,
    with_wins: 16,
    without_count: 20,
    without_wins: 4,
    win_rate_with: 80,
    win_rate_without: 20,
    difference: 60,
    significant: true,
    current_weight: 10,
    suggested_weight: 35,
    note: "",
};

describe("describeCheckCounts", () => {
    it("lists only what happened, with the right singular and plural wording", () => {
        expect(describeCheckCounts({ emails_ok: 1, emails_bad: 3, websites_dead: 1, skipped: 0 })).toEqual([
            "1 email works",
            "3 emails cannot receive mail",
            "1 website is down",
        ]);
    });

    it("returns nothing when nothing was found", () => {
        expect(describeCheckCounts({})).toEqual([]);
    });
});

describe("scoring trait wording", () => {
    it("says how much more or less often a trait closes", () => {
        expect(describeTrait(TRAIT)).toBe("Closes 60 points more often with it");
        expect(describeTrait({ ...TRAIT, difference: -12.5 })).toBe("Closes 12.5 points less often with it");
    });

    it("falls back to the group sizes while there is too little to compare", () => {
        expect(describeTrait({ ...TRAIT, difference: null, with_count: 1, without_count: 0 })).toBe("1 lead with, 0 leads without");
    });

    it("shows the suggested change in weight and tolerates a missing rate", () => {
        expect(weightChange(TRAIT)).toBe(25);
        expect(weightChange({ ...TRAIT, suggested_weight: 4 })).toBe(-6);
        expect(formatRate(80)).toBe("80%");
        expect(formatRate(null)).toBe("—");
    });
});
