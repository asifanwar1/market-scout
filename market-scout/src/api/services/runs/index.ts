import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import type { TApiArgs, TQueryParams, WithSignal } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type {
    TCreateRunBody,
    TGetRunsParams,
    TGetRunTasksParams,
} from "./runs.request.types";
import type {
    TGetRunsResponse,
    TGetRunTasksResponse,
    TRun,
    TRunEstimate,
} from "./runs.response.types";
import { RUN_QUERY_KEYS } from "./queryKeys";

export const GetRuns = async (params?: TGetRunsParams) => {
    return request<TGetRunsResponse>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.RUNS.ROOT,
        params: params as TQueryParams,
    });
};

export const GetRun = async ({ id }: TApiArgs) => {
    return request<TRun>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.RUNS.detail(id),
    });
};

export const GetRunTasks = async ({
    id,
    params,
}: TApiArgs<undefined, TGetRunTasksParams>) => {
    return request<TGetRunTasksResponse>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.RUNS.tasks(id),
        params: params as TQueryParams,
    });
};

export const EstimateRun = async (body: WithSignal<TCreateRunBody>) => {
    const { signal, ...payload } = body;
    return request<TRunEstimate, TCreateRunBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.RUNS.ESTIMATE,
        body: payload,
        signal,
        silent: true,
    });
};

export const CreateRun = async (body: TCreateRunBody) => {
    return request<TRun, TCreateRunBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.RUNS.ROOT,
        body,
    });
};

export const CancelRun = async ({ id }: TApiArgs) => {
    return request<TRun>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.RUNS.cancel(id),
    });
};

export const ResumeRun = async ({ id }: TApiArgs) => {
    return request<TRun>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.RUNS.resume(id),
    });
};

export { RUN_QUERY_KEYS };
