import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import type { PropsWithChildren } from "react";

import { queryClient } from "@/lib/queryClient";

const ApiClientProvider = ({ children }: PropsWithChildren) => {
    return (
        <QueryClientProvider client={queryClient}>
            {children}
            {/* Dev only. Bottom-right: the left edge is the sidebar's user menu. */}
            <ReactQueryDevtools buttonPosition="bottom-right" />
        </QueryClientProvider>
    );
};

export default ApiClientProvider;
