import { request } from "@/api/client/request";
import type { TRun } from "@/api/services/runs/runs.response.types";
import type { TApiArgs, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type { TCreateScheduleBody, TGetSchedulesParams, TUpdateScheduleBody } from "./schedules.request.types";
import type { TGetSchedulesResponse, TSchedule } from "./schedules.response.types";
import { SCHEDULE_QUERY_KEYS } from "./queryKeys";

export const GetSchedules = (params?: TGetSchedulesParams) =>
    request<TGetSchedulesResponse>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.SCHEDULES.ROOT,
        params: params as TQueryParams,
    });

export const CreateSchedule = (body: TCreateScheduleBody) =>
    request<TSchedule, TCreateScheduleBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.SCHEDULES.ROOT, body });

export const UpdateSchedule = ({ id, body }: TApiArgs<TUpdateScheduleBody>) =>
    request<TSchedule, TUpdateScheduleBody>({ method: HTTP_METHODS.PUT, url: ENDPOINTS.SCHEDULES.detail(id), body });

export const DeleteSchedule = ({ id }: TApiArgs) =>
    request<void>({ method: HTTP_METHODS.DELETE, url: ENDPOINTS.SCHEDULES.detail(id) });

export const RunScheduleNow = ({ id }: TApiArgs) =>
    request<TRun>({ method: HTTP_METHODS.POST, url: ENDPOINTS.SCHEDULES.runNow(id) });

export { SCHEDULE_QUERY_KEYS };
