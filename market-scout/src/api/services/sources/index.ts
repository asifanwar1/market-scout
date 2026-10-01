import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import type { TApiArgs } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type { TUpdateSourceBody } from "./sources.request.types";
import type {
    TGetSourcesResponse,
    TSource,
    TSourceTestResponse,
} from "./sources.response.types";
import { SOURCE_QUERY_KEYS } from "./queryKeys";

export const GetSources = async () => {
    return request<TGetSourcesResponse>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.SOURCES.ROOT,
    });
};

export const UpdateSource = async ({ key, body }: TApiArgs<TUpdateSourceBody>) => {
    return request<TSource, TUpdateSourceBody>({
        method: HTTP_METHODS.PUT,
        url: ENDPOINTS.SOURCES.detail(key),
        body,
    });
};

export const TestSource = async ({ key }: TApiArgs) => {
    return request<TSourceTestResponse>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.SOURCES.test(key),
        silent: true,
    });
};

export { SOURCE_QUERY_KEYS };
