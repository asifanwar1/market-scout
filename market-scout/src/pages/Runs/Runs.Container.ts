import { parseAsStringLiteral, useQueryStates } from "nuqs";
import { useNavigate } from "react-router-dom";

import type { TRun } from "@/api/services/runs/runs.response.types";
import { ALL_OPTION_VALUE, FIRST_PAGE } from "@/constants";
import { RUN_STATUS_OPTIONS, type RunStatus } from "@/constants/run-status.constants";
import { useGetRuns } from "@/hooks/api/runs.queries";
import { APP_ROUTES } from "@/routes/appRoutes";
import { paginationUrlState } from "@/utils/listUrlState";

const STATUSES = RUN_STATUS_OPTIONS.map((option) => option.value) as [RunStatus, ...RunStatus[]];

const urlState = {
    status: parseAsStringLiteral(STATUSES),
    ...paginationUrlState,
};

export const useRunsPage = () => {
    const navigate = useNavigate();
    const [state, setState] = useQueryStates(urlState, { history: "replace" });

    const { data, isPending } = useGetRuns({
        status: state.status ?? undefined,
        page: state.page,
        limit: state.size,
    });
    const runs = data?.data ?? [];
    const total = data?.count ?? 0;
    const hasRuns = total > 0;
    const hasStatusFilter = state.status !== null;
    const statusValue = state.status ?? ALL_OPTION_VALUE;
    const page = state.page;
    const pageSize = state.size;
    const emptyTitle = hasStatusFilter ? "No runs with this status" : "No runs yet";

    const getRunRowId = (run: TRun) => String(run.id);

    const openRun = (run: TRun) => {
        navigate(APP_ROUTES.RUNS_DETAILS.replace(":id", String(run.id)));
    };

    const onStatusChange = (value: string) => {
        const status = value === ALL_OPTION_VALUE ? null : (value as RunStatus);
        void setState({ status, page: FIRST_PAGE });
    };

    const onPageChange = (nextPage: number) => {
        void setState({ page: nextPage });
    };

    const onPageSizeChange = (size: number) => {
        void setState({ size, page: FIRST_PAGE });
    };

    return {
        runs,
        total,
        hasRuns,
        hasStatusFilter,
        statusValue,
        page,
        pageSize,
        emptyTitle,
        isPending,
        getRunRowId,
        openRun,
        onStatusChange,
        onPageChange,
        onPageSizeChange,
    };
};
