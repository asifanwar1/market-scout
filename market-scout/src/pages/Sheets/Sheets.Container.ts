import { useState } from "react";

import { useGetSheetsSettings, useSyncSheets } from "@/hooks/api/sheets.queries";
import { showToast } from "@/lib/toast";
import { pluralize } from "@/utils/format.utils";

import { FAST_POLL_MS } from "@/constants/timing.constants";
import { MAX_POLLS } from "./Sheets.constants";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const useSheetsPage = () => {
    const { data: settings, isPending, refetch } = useGetSheetsSettings();
    const { mutateAsync: startSync } = useSyncSheets();
    const [isStarting, setIsStarting] = useState(false);

    const syncNow = async () => {
        setIsStarting(true);
        try {
            let result = await startSync();
            for (let poll = 0; result.is_syncing && poll < MAX_POLLS; poll++) {
                await sleep(FAST_POLL_MS);
                result = (await refetch()).data ?? result;
            }
            if (result.last_sync_ok) {
                showToast.success(`Sheet updated: ${pluralize(result.last_row_count ?? 0, "lead", "leads")}`);
            } else if (result.last_sync_ok === false) {
                showToast.error(result.last_error ?? "The sheet couldn't be updated");
            }
        } finally {
            setIsStarting(false);
        }
    };

    const isSyncing = Boolean(settings?.is_syncing) || isStarting;
    const isReady = !isPending && Boolean(settings);
    const isSetupOpenByDefault = !settings?.is_configured;

    return {
        settings,
        isReady,
        isSyncing,
        isSetupOpenByDefault,
        syncNow,
    };
};

export type TSheetsPage = ReturnType<typeof useSheetsPage>;
