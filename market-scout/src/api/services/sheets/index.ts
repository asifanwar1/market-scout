import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import type { TApiArgs } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { SHEETS_QUERY_KEYS } from "./queryKeys";
import type { TUpdateSheetsBody } from "./sheets.request.types";
import type { TSheetsSettings, TSheetsTestResponse } from "./sheets.response.types";

export const GetSheetsSettings = async () => {
    return request<TSheetsSettings>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.SHEETS.ROOT,
    });
};

export const UpdateSheetsSettings = async ({ body }: TApiArgs<TUpdateSheetsBody>) => {
    return request<TSheetsSettings, TUpdateSheetsBody>({
        method: HTTP_METHODS.PUT,
        url: ENDPOINTS.SHEETS.ROOT,
        body,
    });
};

export const TestSheets = async () => {
    return request<TSheetsTestResponse>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.SHEETS.TEST,
        silent: true,
    });
};

export const SyncSheets = async () => {
    return request<TSheetsSettings>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.SHEETS.SYNC,
    });
};

export { SHEETS_QUERY_KEYS };
