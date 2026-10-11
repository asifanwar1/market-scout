import { useQuery } from "@tanstack/react-query";

import { GetJobsStatus, JOB_QUERY_KEYS } from "@/api";
import { JOBS_POLL_MS } from "@/constants/timing.constants";
import { useStore } from "@/store";

export const useGetJobsStatus = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [JOB_QUERY_KEYS.STATUS],
        enabled: isAuthenticated,
        queryFn: GetJobsStatus,
        refetchInterval: JOBS_POLL_MS,
    });
};
