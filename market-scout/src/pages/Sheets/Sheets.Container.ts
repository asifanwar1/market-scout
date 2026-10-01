import { useState } from "react";

import { useGetSheetsSettings, useSyncSheets } from "@/hooks/api/sheets.queries";
import { showToast } from "@/lib/toast";
import { pluralize } from "@/utils/format.utils";

const POLL_MS = 1500;
// A sync of a very large sheet still finishes well inside this; after it we stop watching (the
// page keeps polling by itself while the server says it is syncing).
const MAX_POLLS = 200;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const useSheetsPage = () => {
    const { data: settings, isPending, refetch } = useGetSheetsSettings();
    const { mutateAsync: startSync } = useSyncSheets();
    const [isStarting, setIsStarting] = useState(false);

    // "Sync now" returns at once and the work carries on in the background: watch it finish so
    // the person gets an answer instead of a spinner that never says what happened.
    const syncNow = async () => {
        setIsStarting(true);
        try {
            let result = await startSync();
            for (let poll = 0; result.is_syncing && poll < MAX_POLLS; poll++) {
                await sleep(POLL_MS);
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

    return {
        settings,
        isPending,
        isSyncing: Boolean(settings?.is_syncing) || isStarting,
        syncNow,
    };
};

export type TSheetsPage = ReturnType<typeof useSheetsPage>;
