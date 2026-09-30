import { useMutation } from "@tanstack/react-query";

import {
    BUSINESS_QUERY_KEYS,
    CreateGeography,
    DeleteGeography,
    GEOGRAPHY_QUERY_KEYS,
    UpdateGeography,
} from "@/api";
import type {
    TCreateGeographyBody,
    TUpdateGeographyBody,
} from "@/api/services/geographies/geographies.request.types";
import { queryClient } from "@/lib/queryClient";
import { invalidateMultiple } from "@/utils/common.utils";

// Lead rows show their city and province, so a rename or delete must refresh them too.
const refreshGeographies = () =>
    invalidateMultiple(queryClient, [
        [GEOGRAPHY_QUERY_KEYS.TREE],
        [BUSINESS_QUERY_KEYS.BUSINESSES],
    ]);

export const useCreateGeography = () =>
    useMutation({
        mutationFn: (body: TCreateGeographyBody) => CreateGeography(body),
        onSuccess: refreshGeographies,
    });

export const useUpdateGeography = () =>
    useMutation({
        mutationFn: ({ id, body }: { id: number; body: TUpdateGeographyBody }) =>
            UpdateGeography({ id, body }),
        onSuccess: refreshGeographies,
    });

export const useDeleteGeography = () =>
    useMutation({
        mutationFn: (id: number) => DeleteGeography({ id }),
        onSuccess: refreshGeographies,
    });
