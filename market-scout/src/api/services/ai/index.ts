import { request } from "@/api/client/request";
import type { TApiArgs } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type { TAiEstimateBody, TAiSettingsBody, TApplySegmentBody } from "./ai.request.types";
import type {
    TAiBatch,
    TAiEstimate,
    TAiResult,
    TAiSettings,
    TAiStatus,
    TAiTestResponse,
} from "./ai.response.types";
import { AI_QUERY_KEYS } from "./queryKeys";

export const GetAiSettings = () => request<TAiSettings>({ method: HTTP_METHODS.GET, url: ENDPOINTS.AI.SETTINGS });

export const UpdateAiSettings = (body: TAiSettingsBody) =>
    request<TAiSettings, TAiSettingsBody>({ method: HTTP_METHODS.PUT, url: ENDPOINTS.AI.SETTINGS, body });

export const TestAi = () => request<TAiTestResponse>({ method: HTTP_METHODS.POST, url: ENDPOINTS.AI.TEST });

export const GetAiStatus = () => request<TAiStatus>({ method: HTTP_METHODS.GET, url: ENDPOINTS.AI.STATUS, silent: true });

export const EstimateAi = (body: TAiEstimateBody) =>
    request<TAiEstimate, TAiEstimateBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.AI.ESTIMATE, body });

export const StartAiAnalysis = (body: TAiEstimateBody) =>
    request<TAiBatch, TAiEstimateBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.AI.ANALYZE, body });

export const GetAiBatch = ({ id }: TApiArgs) =>
    request<TAiBatch>({ method: HTTP_METHODS.GET, url: ENDPOINTS.AI.batch(id), silent: true });

export const ApplyAiSegment = ({ id, body }: TApiArgs<TApplySegmentBody>) =>
    request<TAiResult, TApplySegmentBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.AI.applySegment(id), body });

export { AI_QUERY_KEYS };
