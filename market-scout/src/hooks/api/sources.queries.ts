import { useMutation } from "@tanstack/react-query";

import { SOURCE_QUERY_KEYS, TestSource, UpdateSource } from "@/api";
import type { TUpdateSourceBody } from "@/api/services/sources/sources.request.types";
import { queryClient } from "@/lib/queryClient";
import { invalidateMultiple } from "@/utils/common.utils";

export const useUpdateSource = () =>
    useMutation({
        mutationFn: ({ key, body }: { key: string; body: TUpdateSourceBody }) => UpdateSource({ key, body }),
        onSuccess: () => invalidateMultiple(queryClient, [[SOURCE_QUERY_KEYS.SOURCES]]),
    });

export const useTestSource = () =>
    useMutation({
        mutationFn: (key: string) => TestSource({ key }),
    });
