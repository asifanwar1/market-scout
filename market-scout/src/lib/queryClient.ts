import { QueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { CACHE_TIME, HTTP_STATUS, STALE_TIME } from "@/constants";
import { MAX_QUERY_RETRIES } from "@/constants/timing.constants";

const handleRetry = (failCount: number, error: Error) => {
    const status = isAxiosError(error) ? error.response?.status : undefined;
    if (status !== undefined && status >= HTTP_STATUS.BAD_REQUEST && status < HTTP_STATUS.INTERNAL_SERVER_ERROR) {
        return false;
    }
    return failCount < MAX_QUERY_RETRIES;
};

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            networkMode: "online",
            staleTime: STALE_TIME,
            gcTime: CACHE_TIME,
            retry: handleRetry,
            refetchOnWindowFocus: false,
            throwOnError: false,
        },
        mutations: {
            networkMode: "online",
            retry: false,
        },
    },
});
