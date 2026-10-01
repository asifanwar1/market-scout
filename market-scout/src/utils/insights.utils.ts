import { format } from "date-fns";

import type { TInsightBucket } from "@/api/services/insights/insights.response.types";

export const percent = (part: number, whole: number): string =>
    whole > 0 ? `${Math.round((100 * part) / whole)}%` : "—";

export const heatLevel = (count: number, max: number): 0 | 1 | 2 | 3 | 4 => {
    if (count <= 0 || max <= 0) return 0;
    const share = count / max;
    if (share > 0.75) return 4;
    if (share > 0.5) return 3;
    if (share > 0.25) return 2;
    return 1;
};

export const periodLabel = (period: string, bucket: TInsightBucket): string => {
    const date = new Date(`${period}T00:00:00`);
    return bucket === "month" ? format(date, "MMM yyyy") : format(date, "d MMM");
};

export const joinNames = (names: string[]): string => {
    if (names.length <= 1) return names.join("");
    return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
};
