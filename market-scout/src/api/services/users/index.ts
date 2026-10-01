import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import type { UserModel } from "@/api/models/user.model";
import type { TApiArgs, TListResponse, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type {
    TCreateUserBody,
    TGetUsersParams,
    TUpdateUserBody,
} from "./users.request.types";
import { USER_QUERY_KEYS } from "./queryKeys";

export const GetUsers = async (params?: TGetUsersParams) => {
    return request<TListResponse<UserModel>>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.USERS.ROOT,
        params: params as TQueryParams,
    });
};

export const CreateUser = async (body: TCreateUserBody) => {
    return request<UserModel, TCreateUserBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.USERS.ROOT,
        body,
    });
};

export const UpdateUser = async ({ id, body }: TApiArgs<TUpdateUserBody>) => {
    return request<UserModel, TUpdateUserBody>({
        method: HTTP_METHODS.PUT,
        url: ENDPOINTS.USERS.detail(id),
        body,
    });
};

export { USER_QUERY_KEYS };
