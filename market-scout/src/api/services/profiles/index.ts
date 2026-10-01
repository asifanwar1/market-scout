import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import type { TApiArgs, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type { TGetProfilesParams, TProfileBody } from "./profiles.request.types";
import type {
    TGetProfilesResponse,
    TProfileDetail,
} from "./profiles.response.types";
import { PROFILE_QUERY_KEYS } from "./queryKeys";

export const GetProfiles = async (params?: TGetProfilesParams) => {
    return request<TGetProfilesResponse>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.PROFILES.ROOT,
        params: params as TQueryParams,
    });
};

export const GetProfile = async ({ id }: TApiArgs) => {
    return request<TProfileDetail>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.PROFILES.detail(id),
    });
};

export const CreateProfile = async (body: TProfileBody) => {
    return request<TProfileDetail, TProfileBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.PROFILES.ROOT,
        body,
    });
};

export const UpdateProfile = async ({ id, body }: TApiArgs<TProfileBody>) => {
    return request<TProfileDetail, TProfileBody>({
        method: HTTP_METHODS.PUT,
        url: ENDPOINTS.PROFILES.detail(id),
        body,
    });
};

export const DeleteProfile = async ({ id }: TApiArgs) => {
    return request<void>({
        method: HTTP_METHODS.DELETE,
        url: ENDPOINTS.PROFILES.detail(id),
    });
};

export { PROFILE_QUERY_KEYS };
