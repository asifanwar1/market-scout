import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import { HTTP_METHODS } from "@/constants";
import { INSIGHT_QUERY_KEYS } from "./queryKeys";
import type { ConversionGroup } from "@/constants/pipeline.constants";
import type {
    TConversion,
    TCoverage,
    TGaps,
    TInsightBucket,
    TMovers,
    TOverview,
    TPipeline,
    TSourcesQuality,
    TTimeline,
} from "./insights.response.types";

const get = <T>(url: string, params?: Record<string, number | string | undefined>) =>
    request<T>({ method: HTTP_METHODS.GET, url, params });

export const GetOverview = (profileId?: number) => get<TOverview>(ENDPOINTS.INSIGHTS.OVERVIEW, { profile_id: profileId });

export const GetCoverage = (profileId: number) => get<TCoverage>(ENDPOINTS.INSIGHTS.COVERAGE, { profile_id: profileId });

export const GetGaps = (profileId: number, threshold: number) =>
    get<TGaps>(ENDPOINTS.INSIGHTS.GAPS, { profile_id: profileId, threshold });

export const GetTimeline = (profileId: number | undefined, days: number, bucket: TInsightBucket) =>
    get<TTimeline>(ENDPOINTS.INSIGHTS.TIMELINE, { profile_id: profileId, days, bucket });

export const GetSourcesQuality = (profileId?: number) =>
    get<TSourcesQuality>(ENDPOINTS.INSIGHTS.SOURCES, { profile_id: profileId });

export const GetMovers = (profileId: number | undefined, days: number) =>
    get<TMovers>(ENDPOINTS.INSIGHTS.MOVERS, { profile_id: profileId, days });

export const GetPipeline = (profileId?: number) => get<TPipeline>(ENDPOINTS.INSIGHTS.PIPELINE, { profile_id: profileId });

export const GetConversion = (profileId: number | undefined, groupBy: ConversionGroup) =>
    get<TConversion>(ENDPOINTS.INSIGHTS.CONVERSION, { profile_id: profileId, group_by: groupBy });

export { INSIGHT_QUERY_KEYS };
