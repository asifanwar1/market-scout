import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import { BUSINESS_QUERY_KEYS, CreateUser, GetUsers, UpdateUser, USER_QUERY_KEYS } from "@/api";
import type {
    TCreateUserBody,
    TGetUsersParams,
    TUpdateUserBody,
} from "@/api/services/users/users.request.types";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

export const useGetUsers = (params: TGetUsersParams) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [USER_QUERY_KEYS.USERS, params],
        enabled: isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetUsers(params),
    });
};

const refreshUsers = () =>
    invalidateMultiple(queryClient, [
        [USER_QUERY_KEYS.USERS],
        [BUSINESS_QUERY_KEYS.ASSIGNEES],
    ]);

export const useCreateUser = () =>
    useMutation({
        mutationFn: (body: TCreateUserBody) => CreateUser(body),
        onSuccess: refreshUsers,
    });

export const useUpdateUser = () =>
    useMutation({
        mutationFn: ({ id, body }: { id: number; body: TUpdateUserBody }) => UpdateUser({ id, body }),
        onSuccess: refreshUsers,
    });
