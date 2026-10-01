import { useMutation, useQuery } from "@tanstack/react-query";

import { GetSheetsSettings, SHEETS_QUERY_KEYS, SyncSheets, TestSheets, UpdateSheetsSettings } from "@/api";
import type { TUpdateSheetsBody } from "@/api/services/sheets/sheets.request.types";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";

const POLL_MS = 1500;

export const useGetSheetsSettings = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [SHEETS_QUERY_KEYS.SHEETS],
        enabled: isAuthenticated,
        queryFn: GetSheetsSettings,
        // A refresh can also start by itself (a run finished, a lead was edited): watch it finish.
        refetchInterval: (query) => (query.state.data?.is_syncing ? POLL_MS : false),
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
        // A test can learn the spreadsheet's title, which the settings show.
        onSuccess: () => queryClient.invalidateQueries({ queryKey: [SHEETS_QUERY_KEYS.SHEETS] }),
    });

export const useSyncSheets = () =>
    useMutation({
        mutationFn: SyncSheets,
        onSuccess: (data) => queryClient.setQueryData([SHEETS_QUERY_KEYS.SHEETS], data),
    });
