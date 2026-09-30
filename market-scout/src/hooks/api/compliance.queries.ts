import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import {
    AddDoNotContact,
    BUSINESS_QUERY_KEYS,
    COMPLIANCE_QUERY_KEYS,
    GetDoNotContact,
    RemoveDoNotContact,
} from "@/api";
import type {
    TAddDoNotContactBody,
    TGetDoNotContactParams,
} from "@/api/services/compliance";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

export const useGetDoNotContact = (params: TGetDoNotContactParams) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [COMPLIANCE_QUERY_KEYS.DO_NOT_CONTACT, params],
        enabled: isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetDoNotContact(params),
    });
};

// Blocking hides leads and lifting a block brings them back, so the lead lists refresh too.
const refreshCompliance = () =>
    invalidateMultiple(queryClient, [
        [COMPLIANCE_QUERY_KEYS.DO_NOT_CONTACT],
        [BUSINESS_QUERY_KEYS.BUSINESSES],
    ]);

export const useAddDoNotContact = () =>
    useMutation({
        mutationFn: (body: TAddDoNotContactBody) => AddDoNotContact(body),
        onSuccess: refreshCompliance,
    });

export const useRemoveDoNotContact = () =>
    useMutation({
        mutationFn: (id: number) => RemoveDoNotContact({ id }),
        onSuccess: refreshCompliance,
    });
