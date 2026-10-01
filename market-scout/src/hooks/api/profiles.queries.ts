import { useMutation, useQuery } from "@tanstack/react-query";

import {
    CreateProfile,
    DeleteProfile,
    GetProfiles,
    PROFILE_QUERY_KEYS,
    UpdateProfile,
} from "@/api";
import type { TProfileBody } from "@/api/services/profiles/profiles.request.types";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";
import { LIST_FETCH_LIMIT } from "@/constants/limits.constants";

export const useGetAllProfiles = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [PROFILE_QUERY_KEYS.PROFILES, "all"],
        enabled: isAuthenticated,
        queryFn: () => GetProfiles({ limit: LIST_FETCH_LIMIT }),
    });
};

const refreshProfiles = () =>
    invalidateMultiple(queryClient, [
        [PROFILE_QUERY_KEYS.PROFILES],
        [PROFILE_QUERY_KEYS.PROFILE],
    ]);

export const useCreateProfile = () =>
    useMutation({
        mutationFn: (body: TProfileBody) => CreateProfile(body),
        onSuccess: refreshProfiles,
    });

export const useUpdateProfile = () =>
    useMutation({
        mutationFn: ({ id, body }: { id: number; body: TProfileBody }) => UpdateProfile({ id, body }),
        onSuccess: refreshProfiles,
    });

export const useDeleteProfile = () =>
    useMutation({
        mutationFn: (id: number) => DeleteProfile({ id }),
        onSuccess: refreshProfiles,
    });
