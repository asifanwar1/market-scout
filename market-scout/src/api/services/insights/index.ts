import { request } from "@/api/client/request";
import { HTTP_METHODS } from "@/constants";
import { INSIGHT_QUERY_KEYS } from "./queryKeys";
import type {
    TCoverage,
    TGaps,
    TInsightBucket,
    TMovers,
    TOverview,
    TSourcesQuality,
    TTimeline,
} from "./insights.response.types";

const get = <T>(url: string, params?: Record<string, number | string | undefined>) =>
    request<T>({ method: HTTP_METHODS.GET, url: `/insights/${url}`, params });

export const GetOverview = (profileId?: number) => get<TOverview>("overview", { profile_id: profileId });

export const GetCoverage = (profileId: number) => get<TCoverage>("coverage", { profile_id: profileId });

export const GetGaps = (profileId: number, threshold: number) =>
    get<TGaps>("gaps", { profile_id: profileId, threshold });

export const GetTimeline = (profileId: number | undefined, days: number, bucket: TInsightBucket) =>
    get<TTimeline>("timeline", { profile_id: profileId, days, bucket });

export const GetSourcesQuality = (profileId?: number) =>
    get<TSourcesQuality>("sources", { profile_id: profileId });

export const GetMovers = (profileId: number | undefined, days: number) =>
    get<TMovers>("movers", { profile_id: profileId, days });

export { INSIGHT_QUERY_KEYS };
