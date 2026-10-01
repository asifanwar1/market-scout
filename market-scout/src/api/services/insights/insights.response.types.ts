export type TInsightBucket = "day" | "week" | "month";

export type TOverview = {
    total: number;
    with_phone: number;
    whatsapp_likely: number;
    with_email: number;
    with_website: number;
    new_last_7_days: number;
    new_last_30_days: number;
    by_status: Record<string, number>;
};

export type TCoverageSegment = { slug: string; name: string };

export type TCoverageCity = {
    geography_id: number;
    city: string;
    province: string | null;
    total: number;
    counts: Record<string, number>;
};

export type TCoverage = {
    segments: TCoverageSegment[];
    cities: TCoverageCity[];
    unplaced: number;
};

export type TGapCity = {
    geography_id: number;
    city: string;
    province: string | null;
    total: number;
    reason: "never_searched" | "few_found";
    searches_done: number;
    last_searched_at: string | null;
    missing_segments: string[];
};

export type TGaps = {
    threshold: number;
    data: TGapCity[];
    count: number;
};

export type TTimelinePoint = { period: string; new: number; total: number };

export type TTimeline = {
    bucket: TInsightBucket;
    data: TTimelinePoint[];
};

export type TSourceQuality = {
    key: string;
    name: string;
    kind: "discovery" | "enrichment" | "import";
    is_paid: boolean;
    found: number;
    exclusive: number | null;
    with_phone: number;
    with_whatsapp: number;
    with_email: number;
    with_website: number;
    requests: number;
    estimated_cost_usd: number | null;
    cost_per_lead_usd: number | null;
};

export type TSourcesQuality = {
    data: TSourceQuality[];
    count: number;
};

export type TMover = {
    business_id: number;
    name: string;
    city: string | null;
    rating: number | null;
    review_count: number;
    review_change: number;
    previous_seen_at: string;
    latest_seen_at: string;
};

export type TMovers = {
    days: number;
    data: TMover[];
    count: number;
};
