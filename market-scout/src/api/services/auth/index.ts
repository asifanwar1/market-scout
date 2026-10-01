import { ENDPOINTS } from "@/constants/endpoints.constants";
import { request } from "@/api/client/request";
import type { TApiArgs } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import type { TChangePasswordBody, TLoginBody } from "./auth.request.types";
import type {
    TMeResponse,
    TMessageResponse,
    TTokenResponse,
} from "./auth.response.types";
import { AUTH_QUERY_KEYS } from "./queryKeys";
import { AUTH_SCHEME_BEARER } from "@/constants/source.constants";

export const LoginApi = async (body: TLoginBody) => {
    return request<TTokenResponse, TLoginBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.AUTH.LOGIN,
        body,
        skipAuth: true,
    });
};

export const GetMe = async (token?: string) => {
    return request<TMeResponse>({
        method: HTTP_METHODS.GET,
        url: ENDPOINTS.AUTH.ME,
        ...(token && { headers: { Authorization: `${AUTH_SCHEME_BEARER} ${token}` } }),
    });
};

export const LogoutAll = async () => {
    return request<TMessageResponse>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.AUTH.LOGOUT_ALL,
    });
};

export const ChangePassword = async ({
    body,
}: TApiArgs<TChangePasswordBody>) => {
    return request<TTokenResponse, TChangePasswordBody>({
        method: HTTP_METHODS.POST,
        url: ENDPOINTS.AUTH.CHANGE_PASSWORD,
        body,
    });
};

export { AUTH_QUERY_KEYS };
