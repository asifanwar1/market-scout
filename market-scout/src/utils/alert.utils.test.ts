import { describe, expect, it } from "vitest";

import type { TAlertSettings } from "@/api/services/alerts/alerts.response.types";
import { ALERT_SETTING_LIMITS } from "@/constants/alert.constants";
import { parseWholeNumber, toSettingsBody, toSettingsForm } from "./alert.utils";

const SETTINGS: TAlertSettings = {
    new_lead_enabled: true,
    new_lead_min_score: 70,
    growing_enabled: false,
    growing_min_new_reviews: 10,
    growing_min_percent: 20,
    reachable_enabled: true,
    max_per_run: 50,
};

describe("parseWholeNumber", () => {
    it("accepts whole numbers inside the limits, ignoring spaces", () => {
        expect(parseWholeNumber(" 70 ", ALERT_SETTING_LIMITS.SCORE)).toBe(70);
        expect(parseWholeNumber("0", ALERT_SETTING_LIMITS.SCORE)).toBe(0);
        expect(parseWholeNumber("100", ALERT_SETTING_LIMITS.SCORE)).toBe(100);
    });

    it("rejects blanks, decimals, negatives, words and out-of-range numbers", () => {
        for (const text of ["", "  ", "7.5", "-3", "abc", "1e2", "101"]) {
            expect(parseWholeNumber(text, ALERT_SETTING_LIMITS.SCORE)).toBeNull();
        }
        expect(parseWholeNumber("0", ALERT_SETTING_LIMITS.NEW_REVIEWS)).toBeNull();
    });
});

describe("alert settings form", () => {
    it("round-trips the saved settings", () => {
        expect(toSettingsBody(toSettingsForm(SETTINGS))).toEqual(SETTINGS);
    });

    it("refuses to build a body while any number is invalid", () => {
        expect(toSettingsBody({ ...toSettingsForm(SETTINGS), newLeadMinScore: "150" })).toBeNull();
        expect(toSettingsBody({ ...toSettingsForm(SETTINGS), maxPerRun: "" })).toBeNull();
        expect(toSettingsBody({ ...toSettingsForm(SETTINGS), growingMinPercent: "x" })).toBeNull();
    });
});
