import { QueryClient } from "@tanstack/react-query";
import { CACHE_TIME, HTTP_STATUS, STALE_TIME } from "@/constants";

function handleRetry(failCount: number, error: unknown) {
    // Auth failures are handled by the API client (refresh, then sign out); retrying
    // client errors just repeats the same rejection.
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status !== undefined && status >= HTTP_STATUS.BAD_REQUEST && status < HTTP_STATUS.INTERNAL_SERVER_ERROR) {
        return false;
    }
    return failCount < 2;
}

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
