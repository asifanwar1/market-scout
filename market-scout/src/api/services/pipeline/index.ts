import { request } from "@/api/client/request";
import type { TApiArgs, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type {
    TActivityBody,
    TActivityParams,
    TGetTasksParams,
    TTaskBody,
    TTaskSummaryParams,
    TTaskUpdateBody,
} from "./pipeline.request.types";
import type {
    TActivity,
    TActivityList,
    TPipelineConfig,
    TTask,
    TTaskList,
    TTaskSummary,
} from "./pipeline.response.types";
import { PIPELINE_QUERY_KEYS } from "./queryKeys";

export const GetPipelineConfig = () =>
    request<TPipelineConfig>({ method: HTTP_METHODS.GET, url: ENDPOINTS.PIPELINE.CONFIG });

export const GetActivities = ({ id, params }: TApiArgs<undefined, TActivityParams>) =>
    request<TActivityList>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.PIPELINE.activities(id),
        params: params as TQueryParams,
        silent: true,
    });

export const AddActivity = ({ id, body }: TApiArgs<TActivityBody>) =>
    request<TActivity, TActivityBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.PIPELINE.activities(id),
        body,
    });

export const GetTasks = (params: TGetTasksParams) =>
    request<TTaskList>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.PIPELINE.TASKS,
        params: params as TQueryParams,
    });

export const GetTaskSummary = (params: TTaskSummaryParams) =>
    request<TTaskSummary>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.PIPELINE.TASK_SUMMARY,
        params: params as TQueryParams,
        silent: true,
    });

export const CreateTask = ({ id, body }: TApiArgs<TTaskBody>) =>
    request<TTask, TTaskBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.PIPELINE.leadTasks(id),
        body,
    });

export const UpdateTask = ({ id, body }: TApiArgs<TTaskUpdateBody>) =>
    request<TTask, TTaskUpdateBody>({
        method: HTTP_METHODS.PATCH,
        url: ENDPOINTS.PIPELINE.task(id),
        body,
    });

export const DeleteTask = ({ id }: TApiArgs) =>
    request<void>({ method: HTTP_METHODS.DELETE, url: ENDPOINTS.PIPELINE.task(id) });

export { PIPELINE_QUERY_KEYS };
