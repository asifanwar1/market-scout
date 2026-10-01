import { useState } from "react";
import { useParams } from "react-router-dom";

import { ACTIVE_IMPORT_STATUSES, IMPORT_STATUS } from "@/constants/import-status.constants";
import { useCancelImport, useGetImport } from "@/hooks/api/imports.queries";
import { showToast } from "@/lib/toast";

export const useImportDetails = () => {
    const { id } = useParams();
    const importId = Number(id) || undefined;

    const { data: record, isPending, isError } = useGetImport(importId);
    const isActive = !!record && ACTIVE_IMPORT_STATUSES.includes(record.status);

    const { mutateAsync: cancelImport, isPending: isCancelling } = useCancelImport();
    const [showCancel, setShowCancel] = useState(false);

    const openCancel = () => {
        setShowCancel(true);
    };

    const closeCancel = () => {
        setShowCancel(false);
    };

    const handleCancel = async () => {
        if (!importId) return;
        await cancelImport(importId);
        showToast.info("Cancelling: it stops after the batch it is on. What it already added is kept.");
        setShowCancel(false);
    };

    const isLoading = isPending;
    const canCancel = isActive && record?.status !== IMPORT_STATUS.CANCELLING;

    return {
        record,
        isLoading,
        isError,
        isActive,
        canCancel,
        showCancel,
        openCancel,
        closeCancel,
        handleCancel,
        isCancelling,
    };
};
