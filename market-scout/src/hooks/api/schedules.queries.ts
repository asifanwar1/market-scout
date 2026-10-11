import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import {
    CreateSchedule,
    DeleteSchedule,
    GetSchedules,
    RUN_QUERY_KEYS,
    RunScheduleNow,
    SCHEDULE_QUERY_KEYS,
    UpdateSchedule,
} from "@/api";
import type {
    TCreateScheduleBody,
    TGetSchedulesParams,
    TUpdateScheduleBody,
} from "@/api/services/schedules/schedules.request.types";
import { queryClient } from "@/lib/queryClient";
import { useStore } from "@/store";
import { invalidateMultiple } from "@/utils/common.utils";

const refreshSchedules = () => invalidateMultiple(queryClient, [[SCHEDULE_QUERY_KEYS.SCHEDULES]]);

const refreshSchedulesAndRuns = () =>
    invalidateMultiple(queryClient, [[SCHEDULE_QUERY_KEYS.SCHEDULES], [RUN_QUERY_KEYS.RUNS]]);

export const useGetSchedules = (params: TGetSchedulesParams) => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [SCHEDULE_QUERY_KEYS.SCHEDULES, params],
        enabled: isAuthenticated,
        placeholderData: keepPreviousData,
        queryFn: () => GetSchedules(params),
    });
};

export const useCreateSchedule = () => {
    return useMutation({
        mutationFn: (body: TCreateScheduleBody) => CreateSchedule(body),
        onSuccess: refreshSchedules,
    });
};

export const useUpdateSchedule = () => {
    return useMutation({
        mutationFn: ({ id, body }: { id: number; body: TUpdateScheduleBody }) => UpdateSchedule({ id, body }),
        onSuccess: refreshSchedules,
    });
};

export const useDeleteSchedule = () => {
    return useMutation({
        mutationFn: (id: number) => DeleteSchedule({ id }),
        onSuccess: refreshSchedulesAndRuns,
    });
};

export const useRunScheduleNow = () => {
    return useMutation({
        mutationFn: (id: number) => RunScheduleNow({ id }),
        onSuccess: refreshSchedulesAndRuns,
    });
};
