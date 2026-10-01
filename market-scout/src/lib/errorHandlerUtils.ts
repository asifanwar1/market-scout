import { isAxiosError } from "axios";

import { showToast } from "./toast";
import {
    GENERIC_ERROR_MESSAGE,
    NETWORK_ERROR_MESSAGE,
} from "@/constants/Validation-messages.constants";

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

export const getErrorMessage = (error: Error): string => {
    if (isAxiosError<TBackendErrorData>(error)) {
        return extractErrorMessage(error.response?.data);
    }
    return error.message || GENERIC_ERROR_MESSAGE;
};

export const networkRequestErrorHandler = (error: Error): void => {
    if (isAxiosError<TBackendErrorData>(error)) {
        showToast.error(error.response ? getErrorMessage(error) : NETWORK_ERROR_MESSAGE);
        return;
    }
    showToast.error(getErrorMessage(error));
};
