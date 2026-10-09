import { parseAsBoolean, parseAsStringLiteral, useQueryStates } from "nuqs";

import type { TTask } from "@/api/services/pipeline/pipeline.response.types";
import { FIRST_PAGE, TASK_SCOPE_OPTIONS } from "@/constants";
import { TASK_SCOPE } from "@/constants/pipeline.constants";
import { useGetTasks, useGetTaskSummary, useUpdateTask } from "@/hooks/api/pipeline.queries";
import { showToast } from "@/lib/toast";
import { paginationUrlState } from "@/utils/listUrlState";
import { todayStamp } from "@/utils/pipeline.utils";
import { EMPTY_DESCRIPTION, EMPTY_TITLES, TASK_SCOPE_VALUES } from "./Tasks.constants";

const urlState = {
    scope: parseAsStringLiteral(TASK_SCOPE_VALUES).withDefault(TASK_SCOPE.OPEN),
    mine: parseAsBoolean.withDefault(true),
    ...paginationUrlState,
};

export const useTasksPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const today = todayStamp();

    const { data, isPending } = useGetTasks({
        scope: state.scope,
        mine: state.mine,
        today,
        page: state.page,
        limit: state.size,
    });
    const { data: summary } = useGetTaskSummary(today);
    const { mutateAsync: updateTask, isPending: isUpdating } = useUpdateTask();

    const tasks = data?.data ?? [];
    const total = data?.count ?? 0;
    const hasTasks = total > 0;
    const scope = state.scope;
    const mine = state.mine;
    const page = state.page;
    const pageSize = state.size;
    const isDoneView = scope === TASK_SCOPE.DONE;
    const emptyTitle = EMPTY_TITLES[scope];
    const emptyDescription = EMPTY_DESCRIPTION;
    const overdueCount = summary?.overdue ?? 0;
    const dueTodayCount = summary?.due_today ?? 0;
    const scopeOptions = TASK_SCOPE_OPTIONS;

    const onScopeChange = (value: string) => {
        const next = TASK_SCOPE_VALUES.find((candidate) => candidate === value);
        if (next) void setState({ scope: next, page: FIRST_PAGE });
    };

    const onMineChange = (checked: boolean) => {
        void setState({ mine: checked, page: FIRST_PAGE });
    };

    const onPageChange = (next: number) => {
        void setState({ page: next });
    };

    const onPageSizeChange = (next: number) => {
        void setState({ size: next, page: FIRST_PAGE });
    };

    const toggleDone = async (task: TTask) => {
        const done = task.completed_at === null;
        await updateTask({ id: task.id, body: { done } });
        showToast.success(done ? "Marked done" : "Reopened");
    };

    return {
        tasks,
        total,
        hasTasks,
        scope,
        scopeOptions,
        mine,
        page,
        pageSize,
        today,
        isPending,
        isUpdating,
        isDoneView,
        emptyTitle,
        emptyDescription,
        overdueCount,
        dueTodayCount,
        onScopeChange,
        onMineChange,
        onPageChange,
        onPageSizeChange,
        toggleDone,
    };
};
