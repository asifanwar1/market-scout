import { parseAsInteger, useQueryState } from "nuqs";
import { useState } from "react";

import type { TInsightBucket } from "@/api/services/insights/insights.response.types";
import { useGetProfiles } from "@/hooks/api/catalog.queries";
import {
    useGetCoverage,
    useGetGaps,
    useGetMovers,
    useGetOverview,
    useGetSourcesQuality,
    useGetTimeline,
} from "@/hooks/api/insights.queries";

export const RANGES = [
    { value: "30", label: "Last 30 days", days: 30, bucket: "day" as TInsightBucket },
    { value: "90", label: "Last 3 months", days: 90, bucket: "week" as TInsightBucket },
    { value: "365", label: "Last year", days: 365, bucket: "month" as TInsightBucket },
];

export const DEFAULT_GAP_THRESHOLD = 5;

export const useInsightsPage = () => {
    const { data: profilesData, isPending: isProfilesLoading } = useGetProfiles();
    const profiles = profilesData?.data ?? [];

    // The chosen profile lives in the URL so a view can be shared.
    const [chosenProfile, setChosenProfile] = useQueryState("profile", parseAsInteger);
    const profileId = chosenProfile ?? profiles[0]?.id;

    const [rangeValue, setRangeValue] = useState(RANGES[1].value);
    const range = RANGES.find((item) => item.value === rangeValue) ?? RANGES[1];
    const [threshold, setThreshold] = useState(DEFAULT_GAP_THRESHOLD);

    const ready = profileId !== undefined;
    const overview = useGetOverview(profileId, ready);
    const coverage = useGetCoverage(profileId);
    const gaps = useGetGaps(profileId, threshold);
    const timeline = useGetTimeline(profileId, range.days, range.bucket, ready);
    const sources = useGetSourcesQuality(profileId, ready);
    const movers = useGetMovers(profileId, 30, ready);

    return {
        profiles,
        isProfilesLoading,
        profileId,
        setProfileId: (id: number) => void setChosenProfile(id),
        range,
        setRangeValue,
        threshold,
        setThreshold,
        overview,
        coverage,
        gaps,
        timeline,
        sources,
        movers,
    };
};

export type TInsightsPage = ReturnType<typeof useInsightsPage>;
