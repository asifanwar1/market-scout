import type { AxiosRequestConfig } from "axios";

import axiosInstance from "./interceptors";
import type {
    THttpMethod,
    TQueryParams,
    TRequestHeaders,
} from "../types/common";

type TRequestConfig<TBody = undefined> = {
    method: THttpMethod;
    url: string;
    headers?: TRequestHeaders;
    params?: TQueryParams;
    body?: TBody;
    signal?: AbortSignal;
    skipAuth?: boolean;
    silent?: boolean;
    responseType?: "json" | "blob";
};

export const request = async <TResponse = void, TBody = undefined>(
    config: TRequestConfig<TBody>,
): Promise<TResponse> => {
    if (config.signal?.aborted) {
        const abortError = new Error("Request aborted");
        abortError.name = "AbortError";
        throw abortError;
    }

    const response = await axiosInstance({
        skipAuth: config.skipAuth,
        silent: config.silent,
        responseType: config.responseType,
        method: config.method,
        url: config.url,
        headers: config.headers,
        params: config.params,
        ...(config.body !== undefined && { data: config.body }),
        ...(config.signal && { signal: config.signal }),
    } as AxiosRequestConfig);

    return response.data as TResponse;
};
