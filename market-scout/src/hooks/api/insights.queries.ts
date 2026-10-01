import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
    GetCoverage,
    GetGaps,
    GetMovers,
    GetOverview,
    GetSourcesQuality,
    GetTimeline,
    INSIGHT_QUERY_KEYS,
} from "@/api";
import type { TInsightBucket } from "@/api/services/insights/insights.response.types";
import { useStore } from "@/store";

// The numbers only move when a run finishes or a lead changes, so a short cache is plenty.
const STALE_TIME = 30 * 1000;

const useInsightQuery = <T>(key: string, params: unknown[], queryFn: () => Promise<T>, enabled = true) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [key, ...params],
        enabled: enabled && isAuthenticated,
        staleTime: STALE_TIME,
        placeholderData: keepPreviousData,
        queryFn,
    });
};

export const useGetOverview = (profileId?: number, enabled = true) =>
    useInsightQuery(INSIGHT_QUERY_KEYS.OVERVIEW, [profileId], () => GetOverview(profileId), enabled);

export const useGetCoverage = (profileId?: number) =>
    useInsightQuery(INSIGHT_QUERY_KEYS.COVERAGE, [profileId], () => GetCoverage(profileId as number), profileId !== undefined);

export const useGetGaps = (profileId: number | undefined, threshold: number) =>
    useInsightQuery(INSIGHT_QUERY_KEYS.GAPS, [profileId, threshold], () => GetGaps(profileId as number, threshold), profileId !== undefined);

export const useGetTimeline = (profileId: number | undefined, days: number, bucket: TInsightBucket, enabled = true) =>
    useInsightQuery(INSIGHT_QUERY_KEYS.TIMELINE, [profileId, days, bucket], () => GetTimeline(profileId, days, bucket), enabled);

export const useGetSourcesQuality = (profileId?: number, enabled = true) =>
    useInsightQuery(INSIGHT_QUERY_KEYS.SOURCES, [profileId], () => GetSourcesQuality(profileId), enabled);

export const useGetMovers = (profileId: number | undefined, days: number, enabled = true) =>
    useInsightQuery(INSIGHT_QUERY_KEYS.MOVERS, [profileId, days], () => GetMovers(profileId, days), enabled);
