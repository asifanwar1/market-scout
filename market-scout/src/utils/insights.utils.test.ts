import { describe, expect, it } from "vitest";

import { heatLevel, joinNames, percent, periodLabel } from "./insights.utils";

describe("percent", () => {
    it("rounds to a whole percent", () => {
        expect(percent(1, 3)).toBe("33%");
        expect(percent(2, 3)).toBe("67%");
        expect(percent(5, 5)).toBe("100%");
    });

    it("shows a dash when there is nothing to divide by", () => {
        expect(percent(0, 0)).toBe("—");
    });

    it("shows 0% when there are leads but none qualify", () => {
        expect(percent(0, 10)).toBe("0%");
    });
});

describe("heatLevel", () => {
    it("leaves empty cells unshaded", () => {
        expect(heatLevel(0, 20)).toBe(0);
        expect(heatLevel(5, 0)).toBe(0);
    });

    it("shades in four steps against the busiest cell", () => {
        expect(heatLevel(1, 20)).toBe(1);
        expect(heatLevel(6, 20)).toBe(2);
        expect(heatLevel(11, 20)).toBe(3);
        expect(heatLevel(20, 20)).toBe(4);
    });

    it("never shades a single lead as the strongest cell unless it is the busiest", () => {
        expect(heatLevel(1, 1)).toBe(4);
        expect(heatLevel(1, 50)).toBe(1);
    });
});

describe("periodLabel", () => {
    it("labels days and weeks by their start date and months by name", () => {
        expect(periodLabel("2026-09-28", "week")).toBe("28 Sep");
        expect(periodLabel("2026-09-05", "day")).toBe("5 Sep");
        expect(periodLabel("2026-09-01", "month")).toBe("Sep 2026");
    });
});

describe("joinNames", () => {
    it("reads as a phrase", () => {
        expect(joinNames([])).toBe("");
        expect(joinNames(["Dealer"])).toBe("Dealer");
        expect(joinNames(["Dealer", "Importer"])).toBe("Dealer and Importer");
        expect(joinNames(["Dealer", "Importer", "Retailer"])).toBe("Dealer, Importer and Retailer");
    });
});
