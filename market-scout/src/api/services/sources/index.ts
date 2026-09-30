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
        url: "/sources/",
    });
};

export const UpdateSource = async ({ key, body }: TApiArgs<TUpdateSourceBody>) => {
    return request<TSource, TUpdateSourceBody>({
        method: HTTP_METHODS.PUT,
        url: `/sources/${key}`,
        body,
    });
};

export const TestSource = async ({ key }: TApiArgs) => {
    return request<TSourceTestResponse>({
        method: HTTP_METHODS.POST,
        url: `/sources/${key}/test`,
        // A failed test is an answer ({ok: false}), not an error, but a 5xx here would be noise too.
        silent: true,
    });
};

export { SOURCE_QUERY_KEYS };
