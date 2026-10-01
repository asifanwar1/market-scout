import { useMutation, useQuery } from "@tanstack/react-query";

import { GetSheetsSettings, SHEETS_QUERY_KEYS, SyncSheets, TestSheets, UpdateSheetsSettings } from "@/api";
import type { TUpdateSheetsBody } from "@/api/services/sheets/sheets.request.types";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { FAST_POLL_MS } from "@/constants/timing.constants";


export const useGetSheetsSettings = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [SHEETS_QUERY_KEYS.SHEETS],
        enabled: isAuthenticated,
        queryFn: GetSheetsSettings,
        refetchInterval: (query) => (query.state.data?.is_syncing ? FAST_POLL_MS : false),
    });
};

export const useUpdateSheetsSettings = () =>
    useMutation({
        mutationFn: (body: TUpdateSheetsBody) => UpdateSheetsSettings({ body }),
        onSuccess: (data) => queryClient.setQueryData([SHEETS_QUERY_KEYS.SHEETS], data),
    });

export const useTestSheets = () =>
    useMutation({
        mutationFn: TestSheets,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: [SHEETS_QUERY_KEYS.SHEETS] }),
    });

export const useSyncSheets = () =>
    useMutation({
        mutationFn: SyncSheets,
        onSuccess: (data) => queryClient.setQueryData([SHEETS_QUERY_KEYS.SHEETS], data),
    });
