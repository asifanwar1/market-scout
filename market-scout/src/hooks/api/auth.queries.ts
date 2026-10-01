import { useMutation, useQuery } from "@tanstack/react-query";

import { AUTH_QUERY_KEYS, GetMe, LoginApi } from "@/api";
import type { TLoginBody } from "@/api/services/auth/auth.request.types";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";

export const useLogin = () => {
    const setAuth = useStore((state) => state.setAuth);

    return useMutation({
        mutationFn: (body: TLoginBody) => LoginApi(body),
        onSuccess: async (tokens) => {
            const user = await GetMe(tokens.access_token);
            setAuth({
                token: tokens.access_token,
                refreshToken: tokens.refresh_token,
                user,
                isAuthenticated: true,
            });
        },
    });
};

export const useLogout = () => {
    const clearAuth = useStore((state) => state.clearAuth);

    return () => {
        clearAuth();
        queryClient.clear();
    };
};

export const useGetMe = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);
    const setAuth = useStore((state) => state.setAuth);

    return useQuery({
        queryKey: [AUTH_QUERY_KEYS.ME],
        enabled: isAuthenticated,
        retry: false,
        queryFn: async () => {
            const user = await GetMe();
            setAuth({ user });
            return user;
        },
    });
};
