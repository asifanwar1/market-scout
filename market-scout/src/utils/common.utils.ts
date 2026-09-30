import type { QueryClient } from "@tanstack/react-query";

export const invalidateMultiple = async (
    client: QueryClient,
    queryKeys: ReadonlyArray<ReadonlyArray<unknown>>,
) => {
    await Promise.all(
        queryKeys.map((queryKey) =>
            client.invalidateQueries({ queryKey: [...queryKey] }),
        ),
    );
};

/** Query-string values arrive as strings; empty means "not set". */
export const emptyToUndefined = <T,>(value: T | "" | null): T | undefined =>
    value === "" || value === null ? undefined : value;
