import { parseAsInteger, parseAsStringLiteral, useQueryStates } from "nuqs";

import Config from "@/Config";
import { RUN_STATUS_OPTIONS } from "@/constants/run-status.constants";
import { useGetRuns } from "@/hooks/api/runs.queries";

const STATUSES = RUN_STATUS_OPTIONS.map((option) => option.value) as [
    (typeof RUN_STATUS_OPTIONS)[number]["value"],
    ...(typeof RUN_STATUS_OPTIONS)[number]["value"][],
];

const urlState = {
    status: parseAsStringLiteral(STATUSES),
    page: parseAsInteger.withDefault(1),
    size: parseAsInteger.withDefault(Config.LIMIT),
};

export const useRunsPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });

    const { data, isPending } = useGetRuns({
        status: state.status ?? undefined,
        page: state.page,
        limit: state.size,
    });

    return {
        state,
        runs: data?.data ?? [],
        total: data?.count ?? 0,
        isLoading: isPending,
        setStatus: (status: (typeof STATUSES)[number] | null) =>
            void setState({ status, page: 1 }),
        setPage: (page: number) => void setState({ page }),
        setPageSize: (size: number) => void setState({ size, page: 1 }),
    };
};
