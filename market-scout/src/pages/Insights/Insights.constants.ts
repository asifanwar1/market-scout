import type { TInsightBucket } from "@/api/services/insights/insights.response.types";

export const INSIGHTS_PAGE_TITLE = "Insights";

export const INSIGHTS_PAGE_DESCRIPTION =
    "What the searches have found so far, where the market is still thin, and which source is pulling its weight.";

export const DEFAULT_GAP_THRESHOLD = 5;
export const MOVERS_DAYS = 30;
export const GAP_THRESHOLD_MIN = 1;
export const GAP_THRESHOLD_MAX = 1000;
export const PROFILE_URL_PARAM = "profile";

export const RANGES: ReadonlyArray<{ value: string; label: string; days: number; bucket: TInsightBucket }> = [
    { value: "30", label: "Last 30 days", days: 30, bucket: "day" },
    { value: "90", label: "Last 3 months", days: 90, bucket: "week" },
    { value: "365", label: "Last year", days: 365, bucket: "month" },
];

export const DEFAULT_RANGE_INDEX = 1;

export const EMPTY_ADMIN_DESCRIPTION = "Start a run and this page fills in with coverage, gaps and source quality.";
export const EMPTY_SALES_DESCRIPTION = "This page fills in once an administrator has run a search.";
