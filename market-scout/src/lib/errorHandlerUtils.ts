import { showToast } from "./toast";
import {
    GENERIC_ERROR_MESSAGE,
    NETWORK_ERROR_MESSAGE,
} from "@/constants/Validation-messages.constants";

// FastAPI answers with { detail: "message" } for our own errors and
// { detail: [{ msg, loc }] } for request-validation errors.
type TBackendErrorData = {
    detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
};

export const extractErrorMessage = (
    data: TBackendErrorData | undefined,
    fallbackMessage: string = GENERIC_ERROR_MESSAGE,
): string => {
    if (!data) return fallbackMessage;

    if (typeof data.detail === "string" && data.detail) {
        return data.detail;
    }

    if (Array.isArray(data.detail)) {
        const messages = data.detail
            .map((item) => item?.msg)
            .filter((msg): msg is string => Boolean(msg));
        if (messages.length) return messages.join(", ");
    }

    return fallbackMessage;
};

export const getErrorMessage = (error: unknown): string => {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: { data?: TBackendErrorData } })
            .response;
        return extractErrorMessage(response?.data);
    }
    if (error instanceof Error) return error.message;
    return GENERIC_ERROR_MESSAGE;
};

/** Shows a toast for a failed request. Sign-out on 401 is handled in the interceptor. */
export const networkRequestErrorHandler = (error: unknown): void => {
    if (typeof error === "object" && error !== null && "response" in error) {
        const response = (error as { response?: unknown }).response;
        if (response) {
            showToast.error(getErrorMessage(error));
            return;
        }
        showToast.error(NETWORK_ERROR_MESSAGE);
        return;
    }
    if (typeof error === "object" && error !== null && "request" in error) {
        showToast.error(NETWORK_ERROR_MESSAGE);
        return;
    }
    showToast.error(getErrorMessage(error));
};
