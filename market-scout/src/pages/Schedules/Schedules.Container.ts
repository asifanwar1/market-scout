import { useQueryStates } from "nuqs";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { TSchedule } from "@/api/services/schedules/schedules.response.types";
import { FIRST_PAGE } from "@/constants";
import { REPEAT_URL_PARAM, REPEAT_URL_VALUE } from "@/constants/schedule.constants";
import { useGetJobsStatus } from "@/hooks/api/jobs.queries";
import { useDeleteSchedule, useGetSchedules, useRunScheduleNow, useUpdateSchedule } from "@/hooks/api/schedules.queries";
import { showToast } from "@/lib/toast";
import { APP_ROUTES } from "@/routes/appRoutes";
import { paginationUrlState } from "@/utils/listUrlState";

const REPEAT_URL = `${APP_ROUTES.RUNS_NEW}?${REPEAT_URL_PARAM}=${REPEAT_URL_VALUE}`;

export const useSchedulesPage = () => {
    const navigate = useNavigate();
    const [state, setState] = useQueryStates(paginationUrlState, { history: "replace" });

    const { data, isPending } = useGetSchedules({ page: state.page, limit: state.size });
    const { data: jobsStatus } = useGetJobsStatus();
    const { mutateAsync: updateSchedule, isPending: isUpdating } = useUpdateSchedule();
    const { mutateAsync: runSchedule, isPending: isStarting } = useRunScheduleNow();
    const { mutateAsync: deleteSchedule, isPending: isDeleting } = useDeleteSchedule();
    const [pendingDelete, setPendingDelete] = useState<TSchedule | null>(null);

    const schedules = data?.data ?? [];
    const total = data?.count ?? 0;
    const hasSchedules = total > 0;
    const page = state.page;
    const pageSize = state.size;
    const isBusy = isUpdating || isStarting || isDeleting;
    const isDeleteOpen = pendingDelete !== null;
    const newRepeatUrl = REPEAT_URL;

    const onPageChange = (next: number) => {
        void setState({ page: next });
    };

    const onPageSizeChange = (next: number) => {
        void setState({ size: next, page: FIRST_PAGE });
    };

    const toggleActive = async (schedule: TSchedule) => {
        const isActive = !schedule.is_active;
        await updateSchedule({ id: schedule.id, body: { is_active: isActive } });
        showToast.success(isActive ? "Switched on" : "Paused");
    };

    const runNow = async (schedule: TSchedule) => {
        const run = await runSchedule(schedule.id);
        showToast.success(`Run #${run.id} started`);
        navigate(APP_ROUTES.RUNS_DETAILS.replace(":id", String(run.id)));
    };

    const requestDelete = (schedule: TSchedule) => {
        setPendingDelete(schedule);
    };

    const closeDelete = () => {
        setPendingDelete(null);
    };

    const confirmDelete = async () => {
        if (!pendingDelete) return;
        await deleteSchedule(pendingDelete.id);
        showToast.success("Repeating search deleted");
        setPendingDelete(null);
    };

    return {
        schedules,
        total,
        hasSchedules,
        page,
        pageSize,
        isPending,
        isBusy,
        isDeleting,
        isDeleteOpen,
        jobsStatus,
        newRepeatUrl,
        onPageChange,
        onPageSizeChange,
        toggleActive,
        runNow,
        requestDelete,
        closeDelete,
        confirmDelete,
    };
};
