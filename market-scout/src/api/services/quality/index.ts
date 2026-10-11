import { request } from "@/api/client/request";
import type { TApiArgs, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type {
    TCheckBody,
    TGetDuplicatesParams,
    TMergeBody,
    TQualitySettingsBody,
    TScoringProfileBody,
} from "./quality.request.types";
import type {
    TGetDuplicatesResponse,
    TMergeResponse,
    TQualitySettings,
    TQualityTask,
    TScoring,
    TScoringApplyResponse,
} from "./quality.response.types";
import { QUALITY_QUERY_KEYS } from "./queryKeys";

export const StartChecks = (body: TCheckBody) =>
    request<TQualityTask, TCheckBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.QUALITY.CHECKS, body });

export const GetQualityTask = ({ id }: TApiArgs) =>
    request<TQualityTask>({ method: HTTP_METHODS.GET, url: ENDPOINTS.QUALITY.task(id), silent: true });

export const GetDuplicates = (params?: TGetDuplicatesParams) =>
    request<TGetDuplicatesResponse>({ method: HTTP_METHODS.GET, url: ENDPOINTS.QUALITY.DUPLICATES, params: params as TQueryParams });

export const ScanDuplicates = () => request<TQualityTask>({ method: HTTP_METHODS.POST, url: ENDPOINTS.QUALITY.DUPLICATES_SCAN });

export const MergeDuplicate = ({ id, body }: TApiArgs<TMergeBody>) =>
    request<TMergeResponse, TMergeBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.QUALITY.merge(id), body });

export const DismissDuplicate = ({ id }: TApiArgs) =>
    request<void>({ method: HTTP_METHODS.POST, url: ENDPOINTS.QUALITY.dismiss(id) });

export const GetScoring = (profileId: number) =>
    request<TScoring>({ method: HTTP_METHODS.GET, url: ENDPOINTS.QUALITY.SCORING, params: { profile_id: profileId } });

export const ApplyScoring = (body: TScoringProfileBody) =>
    request<TScoringApplyResponse, TScoringProfileBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.QUALITY.SCORING_APPLY, body });

export const RevertScoring = (body: TScoringProfileBody) =>
    request<TScoringApplyResponse, TScoringProfileBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.QUALITY.SCORING_REVERT, body });

export const GetQualitySettings = () => request<TQualitySettings>({ method: HTTP_METHODS.GET, url: ENDPOINTS.QUALITY.SETTINGS });

export const UpdateQualitySettings = (body: TQualitySettingsBody) =>
    request<TQualitySettings, TQualitySettingsBody>({ method: HTTP_METHODS.PUT, url: ENDPOINTS.QUALITY.SETTINGS, body });

export { QUALITY_QUERY_KEYS };
