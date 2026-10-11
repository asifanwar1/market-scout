import { request } from "@/api/client/request";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type { TJobsStatus } from "./jobs.response.types";
import { JOB_QUERY_KEYS } from "./queryKeys";

export const GetJobsStatus = () =>
    request<TJobsStatus>({ method: HTTP_METHODS.GET, url: ENDPOINTS.JOBS.STATUS, silent: true });

export { JOB_QUERY_KEYS };
