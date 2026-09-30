import {
    keepPreviousData,
    useMutation,
    useQuery,
} from "@tanstack/react-query";

import {
    BUSINESS_QUERY_KEYS,
    BulkUpdateBusinesses,
    GetAssignees,
    GetBusiness,
    GetBusinesses,
    MarkDoNotContact,
    UpdateBusiness,
} from "@/api";
import type {
    TBulkUpdateBody,
    TDoNotContactBody,
    TGetBusinessesParams,
    TUpdateBusinessBody,
} from "@/api/services/businesses/businesses.request.types";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

export const useGetBusinesses = (
    params: TGetBusinessesParams,
    enabled = true,
) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [BUSINESS_QUERY_KEYS.BUSINESSES, params],
        enabled: enabled && isAuthenticated,
        // Keep the old rows on screen while the next page / filter loads.
        placeholderData: keepPreviousData,
        queryFn: ({ signal }) => GetBusinesses({ ...params, signal }),
    });
};

export const useGetBusiness = (id?: number | null) => {
    return useQuery({
        queryKey: [BUSINESS_QUERY_KEYS.BUSINESS, id],
        enabled: !!id,
        queryFn: () => GetBusiness({ id: id as number }),
    });
};

export const useGetAssignees = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [BUSINESS_QUERY_KEYS.ASSIGNEES],
        enabled: isAuthenticated,
        staleTime: 5 * 60 * 1000,
        queryFn: GetAssignees,
    });
};

const refreshBusinesses = () =>
    invalidateMultiple(queryClient, [
        [BUSINESS_QUERY_KEYS.BUSINESSES],
        [BUSINESS_QUERY_KEYS.BUSINESS],
    ]);

export const useUpdateBusiness = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TUpdateBusinessBody }) =>
            UpdateBusiness({ id, body }),
        onSuccess: async (updated) => {
            // The response is the fresh detail; show it now, then refresh the lists behind it.
            queryClient.setQueryData(
                [BUSINESS_QUERY_KEYS.BUSINESS, updated.id],
                updated,
            );
            await invalidateMultiple(queryClient, [
                [BUSINESS_QUERY_KEYS.BUSINESSES],
            ]);
        },
    });
};

export const useBulkUpdateBusinesses = () => {
    return useMutation({
        mutationFn: (body: TBulkUpdateBody) => BulkUpdateBusinesses(body),
        onSuccess: refreshBusinesses,
    });
};

export const useMarkDoNotContact = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body?: TDoNotContactBody }) =>
            MarkDoNotContact({ id, body }),
        onSuccess: refreshBusinesses,
    });
};
