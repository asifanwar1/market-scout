import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import { CancelImport, CreateImport, GetImport, GetImports, IMPORT_QUERY_KEYS, PreviewImport } from "@/api";
import type { TGetImportsParams, TImportOptions } from "@/api/services/imports/imports.request.types";
import { ACTIVE_IMPORT_STATUSES } from "@/constants/import-status.constants";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";
import { FAST_POLL_MS } from "@/constants/timing.constants";


export const useGetImports = (params: TGetImportsParams) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [IMPORT_QUERY_KEYS.IMPORTS, params],
        enabled: isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetImports(params),
        refetchInterval: (query) =>
            query.state.data?.data.some((item) => ACTIVE_IMPORT_STATUSES.includes(item.status)) ? FAST_POLL_MS : false,
    });
};

export const useGetImport = (id?: number) =>
    useQuery({
        queryKey: [IMPORT_QUERY_KEYS.IMPORT, id],
        enabled: !!id,
        queryFn: () => GetImport({ id: id as number }),
        refetchInterval: (query) =>
            query.state.data && ACTIVE_IMPORT_STATUSES.includes(query.state.data.status) ? FAST_POLL_MS : false,
    });

export const usePreviewImport = () => useMutation({ mutationFn: PreviewImport });

export const useCreateImport = () =>
    useMutation({
        mutationFn: (variables: { file: File; options: TImportOptions }) => CreateImport(variables),
        onSuccess: () => invalidateMultiple(queryClient, [[IMPORT_QUERY_KEYS.IMPORTS]]),
    });

export const useCancelImport = () =>
    useMutation({
        mutationFn: (id: number) => CancelImport({ id }),
        onSuccess: (data) => {
            queryClient.setQueryData([IMPORT_QUERY_KEYS.IMPORT, data.id], data);
            return invalidateMultiple(queryClient, [[IMPORT_QUERY_KEYS.IMPORTS]]);
        },
    });
