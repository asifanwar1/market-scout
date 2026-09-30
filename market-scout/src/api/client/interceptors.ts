import axios, { type InternalAxiosRequestConfig } from "axios";

import Config from "@/Config";
import { HTTP_STATUS } from "@/constants/api.constants";
import { UNAUTHORIZED_ERROR_MESSAGE } from "@/constants/Validation-messages.constants";
import { networkRequestErrorHandler } from "@/lib/errorHandlerUtils";
import { queryClient } from "@/lib/queryClient";
import { showToast } from "@/lib/toast";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store/store";
import type { TTokenResponse } from "@/api/services/auth/auth.response.types";
import axiosInstance from "./axiosInstance";

type TCustomConfig = InternalAxiosRequestConfig & {
    /** Requests that carry no credentials and whose 401 is an answer, not an expired session (login). */
    skipAuth?: boolean;
    /** The caller shows this request's failure itself, so don't also pop a toast. */
    silent?: boolean;
    _retried?: boolean;
};

// Access tokens live 30 minutes; a salesperson works all day. On a 401 we swap the refresh
// token for a new pair once and replay the request. Concurrent 401s share one refresh.
let refreshInFlight: Promise<void> | null = null;

const refreshTokens = async (): Promise<void> => {
    const { refreshToken, setAuth } = useStore.getState();
    if (!refreshToken) throw new Error("No refresh token");

    // A bare axios call: going through axiosInstance would recurse into this interceptor.
    const { data } = await axios.post<TTokenResponse>(
        `${Config.API_URL}/auth/refresh`,
        { refresh_token: refreshToken },
    );
    setAuth({ token: data.access_token, refreshToken: data.refresh_token });
};

const signOut = () => {
    // Several requests can fail together; only the first one announces it.
    const wasSignedIn = useStore.getState().isAuthenticated;
    useStore.getState().clearAuth();
    queryClient.clear();
    if (wasSignedIn) showToast.error(UNAUTHORIZED_ERROR_MESSAGE);
    if (window.location.pathname !== APP_ROUTES.LOGIN) {
        window.location.assign(APP_ROUTES.LOGIN);
    }
};

axiosInstance.interceptors.request.use((config) => {
    if ((config as TCustomConfig).skipAuth) return config;

    const token = useStore.getState().token;
    if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

axiosInstance.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (
            error &&
            typeof error === "object" &&
            "name" in error &&
            (error.name === "CanceledError" || error.name === "AbortError")
        ) {
            return Promise.reject(error);
        }

        const config = error?.config as TCustomConfig | undefined;
        const isUnauthorized =
            error?.response?.status === HTTP_STATUS.UNAUTHORIZED;

        if (isUnauthorized && config && !config.skipAuth) {
            if (!config._retried) {
                config._retried = true;
                try {
                    refreshInFlight ??= refreshTokens().finally(() => {
                        refreshInFlight = null;
                    });
                    await refreshInFlight;
                    return axiosInstance(config);
                } catch {
                    signOut();
                    return Promise.reject(error);
                }
            }
            signOut();
            return Promise.reject(error);
        }

        if (!config?.silent) networkRequestErrorHandler(error);
        return Promise.reject(error);
    },
);

export default axiosInstance;
