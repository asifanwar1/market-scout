import { isAxiosError } from "axios";

import { GENERIC_ERROR_MESSAGE } from "@/constants/Validation-messages.constants";
import { getErrorMessage } from "@/lib/errorHandlerUtils";
import { DATE_STAMP_LENGTH } from "@/constants/limits.constants";
import { OBJECT_URL_REVOKE_DELAY_MS } from "@/constants/timing.constants";

export const saveBlob = (blob: Blob, filename: string): void => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), OBJECT_URL_REVOKE_DELAY_MS);
};

export const getBlobErrorMessage = async (error: Error): Promise<string> => {
    const data = isAxiosError(error) ? error.response?.data : undefined;
    if (data instanceof Blob) {
        try {
            const body = JSON.parse(await data.text()) as { detail?: string };
            if (typeof body.detail === "string" && body.detail) return body.detail;
        } catch {
            return GENERIC_ERROR_MESSAGE;
        }
        return GENERIC_ERROR_MESSAGE;
    }
    return getErrorMessage(error);
};

export const todayStamp = (): string => new Date().toISOString().slice(0, DATE_STAMP_LENGTH);
