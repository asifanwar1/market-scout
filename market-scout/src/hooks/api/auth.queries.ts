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
            // The token isn't in the store yet, so pass it along for this one call.
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

    // Signing out here only ends this browser's session; "logout-all" would end everyone's.
    return () => {
        clearAuth();
        queryClient.clear();
    };
};

/** Keeps the stored user (name, role) in step with the server. */
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
