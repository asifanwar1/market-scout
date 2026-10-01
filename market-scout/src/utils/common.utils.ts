import type { QueryClient } from "@tanstack/react-query";

import type { TQueryKey } from "@/api/types/common";

export const invalidateMultiple = async (
    client: QueryClient,
    queryKeys: ReadonlyArray<TQueryKey>,
) => {
    await Promise.all(
        queryKeys.map((queryKey) =>
            client.invalidateQueries({ queryKey: [...queryKey] }),
        ),
    );
};

export const emptyToUndefined = <T,>(value: T | "" | null): T | undefined =>
    value === "" || value === null ? undefined : value;
