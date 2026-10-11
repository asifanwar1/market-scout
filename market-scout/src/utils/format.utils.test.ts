import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getScheduleFrequencyLabel, SCHEDULE_FREQUENCY } from "@/constants/schedule.constants";
import { formatUpcoming, isWithinDays } from "./format.utils";

const NOW = new Date("2026-10-10T12:00:00Z");

describe("formatUpcoming", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(NOW);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("says how long until a time in the future, reading the server's UTC stamps", () => {
        expect(formatUpcoming("2026-10-17T12:00:00")).toBe("in 7 days");
        expect(formatUpcoming("2026-10-10T15:00:00Z")).toBe("in 3 hours");
    });

    it("says it is about to happen once the time has come or gone", () => {
        expect(formatUpcoming("2026-10-10T11:59:00")).toBe("any moment now");
        expect(formatUpcoming("2026-10-10T12:00:00Z")).toBe("any moment now");
    });

    it("shows a dash when there is no time", () => {
        expect(formatUpcoming(null)).toBe("—");
        expect(formatUpcoming(undefined)).toBe("—");
    });
});

describe("isWithinDays", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(NOW);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("is true for a time inside the window and false outside it", () => {
        expect(isWithinDays("2026-10-05T12:00:00Z", 14)).toBe(true);
        expect(isWithinDays("2026-09-20T12:00:00Z", 14)).toBe(false);
    });

    it("reads the server's UTC stamps that have no zone", () => {
        expect(isWithinDays("2026-10-09T12:00:00", 2)).toBe(true);
    });

    it("is false when there is no time", () => {
        expect(isWithinDays(null, 14)).toBe(false);
        expect(isWithinDays(undefined, 14)).toBe(false);
    });
});

describe("getScheduleFrequencyLabel", () => {
    it("names each frequency in plain words and passes unknown ones through", () => {
        expect(getScheduleFrequencyLabel(SCHEDULE_FREQUENCY.DAILY)).toBe("Every day");
        expect(getScheduleFrequencyLabel(SCHEDULE_FREQUENCY.WEEKLY)).toBe("Every week");
        expect(getScheduleFrequencyLabel(SCHEDULE_FREQUENCY.MONTHLY)).toBe("Every month");
        expect(getScheduleFrequencyLabel("hourly")).toBe("hourly");
    });
});
