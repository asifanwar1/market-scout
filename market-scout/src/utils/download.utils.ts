import { GENERIC_ERROR_MESSAGE } from "@/constants/Validation-messages.constants";
import { getErrorMessage } from "@/lib/errorHandlerUtils";

/** Hands a downloaded blob to the browser as a file. */
export const saveBlob = (blob: Blob, filename: string): void => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Revoked on a later tick: some browsers start reading the blob after click() returns.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
};

/** A failed blob download carries its JSON error as a Blob; read the message out of it. */
export const getBlobErrorMessage = async (error: unknown): Promise<string> => {
    const data = (error as { response?: { data?: unknown } } | null)?.response?.data;
    if (data instanceof Blob) {
        try {
            const body = JSON.parse(await data.text()) as { detail?: unknown };
            if (typeof body.detail === "string" && body.detail) return body.detail;
        } catch {
            return GENERIC_ERROR_MESSAGE;
        }
        return GENERIC_ERROR_MESSAGE;
    }
    return getErrorMessage(error);
};

export const todayStamp = (): string => new Date().toISOString().slice(0, 10);
