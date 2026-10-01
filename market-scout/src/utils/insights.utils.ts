import { format } from "date-fns";

import type { TInsightBucket } from "@/api/services/insights/insights.response.types";

/** 3 of 4 -> "75%". Nothing to divide by shows a dash, not "0%" or "NaN%". */
export const percent = (part: number, whole: number): string =>
    whole > 0 ? `${Math.round((100 * part) / whole)}%` : "—";

/** How strongly to shade a heat-map cell: 0 for empty, 1..4 rising with the count against the busiest cell. */
export const heatLevel = (count: number, max: number): 0 | 1 | 2 | 3 | 4 => {
    if (count <= 0 || max <= 0) return 0;
    const share = count / max;
    if (share > 0.75) return 4;
    if (share > 0.5) return 3;
    if (share > 0.25) return 2;
    return 1;
};

/** A chart label for a bucket's start date ("2026-09-28"): a day, a week starting that day, or a month. */
export const periodLabel = (period: string, bucket: TInsightBucket): string => {
    const date = new Date(`${period}T00:00:00`);
    return bucket === "month" ? format(date, "MMM yyyy") : format(date, "d MMM");
};

/** Names of segments as a short phrase: "Dealer, Importer and Retailer". */
export const joinNames = (names: string[]): string => {
    if (names.length <= 1) return names.join("");
    return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
};
