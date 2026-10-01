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
import { ENDPOINTS } from "@/constants/endpoints.constants";
import { AUTH_SCHEME_BEARER, CANCELLED_ERROR_NAMES } from "@/constants/source.constants";

type TCustomConfig = InternalAxiosRequestConfig & {
    skipAuth?: boolean;
    silent?: boolean;
    _retried?: boolean;
};

let refreshInFlight: Promise<void> | null = null;

const refreshTokens = async (): Promise<void> => {
    const { refreshToken, setAuth } = useStore.getState();
    if (!refreshToken) throw new Error("No refresh token");

    const { data } = await axios.post<TTokenResponse>(
        `${Config.API_URL}${ENDPOINTS.AUTH.REFRESH}`,
        { refresh_token: refreshToken },
    );
    setAuth({ token: data.access_token, refreshToken: data.refresh_token });
};

const signOut = () => {
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
        config.headers.Authorization = `${AUTH_SCHEME_BEARER} ${token}`;
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
            CANCELLED_ERROR_NAMES.includes(String(error.name))
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
