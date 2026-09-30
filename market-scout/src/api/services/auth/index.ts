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

export const LoginApi = async (body: TLoginBody) => {
    return request<TTokenResponse, TLoginBody>({
        method: HTTP_METHODS.POST,
        url: "/auth/login",
        body,
        // A wrong password answers 401; that is a reply for the form, not an expired session.
        skipAuth: true,
    });
};

// `token` lets the caller ask before it has been saved to the store (right after login).
export const GetMe = async (token?: string) => {
    return request<TMeResponse>({
        method: HTTP_METHODS.GET,
        url: "/auth/me",
        ...(token && { headers: { Authorization: `Bearer ${token}` } }),
    });
};

export const LogoutAll = async () => {
    return request<TMessageResponse>({
        method: HTTP_METHODS.POST,
        url: "/auth/logout-all",
    });
};

export const ChangePassword = async ({
    body,
}: TApiArgs<TChangePasswordBody>) => {
    return request<TTokenResponse, TChangePasswordBody>({
        method: HTTP_METHODS.POST,
        url: "/auth/change-password",
        body,
    });
};

export { AUTH_QUERY_KEYS };
