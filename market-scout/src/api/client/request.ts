import type { AxiosRequestConfig } from "axios";

import axiosInstance from "./interceptors";
import type {
    THttpMethod,
    TQueryParams,
    TRequestHeaders,
} from "../types/common";

interface IRequestConfig<TBody = unknown> {
    method: THttpMethod;
    url: string;
    headers?: TRequestHeaders;
    params?: TQueryParams;
    body?: TBody;
    signal?: AbortSignal;
    skipAuth?: boolean;
    silent?: boolean;
}

export const request = async <TResponse = unknown, TBody = unknown>(
    config: IRequestConfig<TBody>,
): Promise<TResponse> => {
    if (config.signal?.aborted) {
        const abortError = new Error("Request aborted");
        abortError.name = "AbortError";
        throw abortError;
    }

    const response = await axiosInstance({
        skipAuth: config.skipAuth,
        silent: config.silent,
        method: config.method,
        url: config.url,
        headers: config.headers,
        params: config.params,
        // An explicit {} is a real body (some endpoints require one), so test for undefined.
        ...(config.body !== undefined && { data: config.body }),
        ...(config.signal && { signal: config.signal }),
    } as AxiosRequestConfig);

    return response.data as TResponse;
};
