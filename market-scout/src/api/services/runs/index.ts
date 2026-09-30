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
        url: "/runs/",
        params: params as TQueryParams,
    });
};

export const GetRun = async ({ id }: TApiArgs) => {
    return request<TRun>({
        method: HTTP_METHODS.GET,
        url: `/runs/${id}`,
    });
};

export const GetRunTasks = async ({
    id,
    params,
}: TApiArgs<undefined, TGetRunTasksParams>) => {
    return request<TGetRunTasksResponse>({
        method: HTTP_METHODS.GET,
        url: `/runs/${id}/tasks`,
        params: params as TQueryParams,
    });
};

export const EstimateRun = async (body: WithSignal<TCreateRunBody>) => {
    const { signal, ...payload } = body;
    return request<TRunEstimate, TCreateRunBody>({
        method: HTTP_METHODS.POST,
        url: "/runs/estimate",
        body: payload,
        signal,
        // The preview refreshes as options change; its errors are shown inline instead.
        silent: true,
    });
};

export const CreateRun = async (body: TCreateRunBody) => {
    return request<TRun, TCreateRunBody>({
        method: HTTP_METHODS.POST,
        url: "/runs/",
        body,
    });
};

export const CancelRun = async ({ id }: TApiArgs) => {
    return request<TRun>({
        method: HTTP_METHODS.POST,
        url: `/runs/${id}/cancel`,
    });
};

export const ResumeRun = async ({ id }: TApiArgs) => {
    return request<TRun>({
        method: HTTP_METHODS.POST,
        url: `/runs/${id}/resume`,
    });
};

export { RUN_QUERY_KEYS };
