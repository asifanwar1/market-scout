import { parseAsBoolean, parseAsStringLiteral, useQueryStates } from "nuqs";

import type { TOutreachMessage } from "@/api/services/outreach/outreach.response.types";
import { ALL_OPTION_VALUE, FIRST_PAGE } from "@/constants";
import { MESSAGE_STATUS_OPTIONS } from "@/constants/outreach.constants";
import { USER_ROLE } from "@/constants/user-role.constants";
import { useGetMessages } from "@/hooks/api/outreach.queries";
import { useStore } from "@/store";
import { paginationUrlState } from "@/utils/listUrlState";
import { LOG_FILTER_STATUS_VALUES } from "./Outreach.constants";

const urlState = {
    mine: parseAsBoolean.withDefault(false),
    status: parseAsStringLiteral(LOG_FILTER_STATUS_VALUES),
    ...paginationUrlState,
};

export const useOutreachPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const user = useStore((store) => store.user);

    const { data, isPending } = useGetMessages({
        mine: state.mine || undefined,
        status: state.status ?? undefined,
        page: state.page,
        limit: state.size,
    });

    const messages: TOutreachMessage[] = data?.data ?? [];
    const total = data?.count ?? 0;
    const hasMessages = total > 0;
    const mineOnly = state.mine;
    const statusValue = state.status ?? ALL_OPTION_VALUE;
    const statusOptions = MESSAGE_STATUS_OPTIONS;
    const page = state.page;
    const pageSize = state.size;
    const isAdmin = user?.role === USER_ROLE.ADMIN;

    const onMineChange = (checked: boolean) => {
        void setState({ mine: checked || null, page: FIRST_PAGE });
    };

    const onStatusChange = (value: string) => {
        const next = LOG_FILTER_STATUS_VALUES.find((candidate) => candidate === value) ?? null;
        void setState({ status: next, page: FIRST_PAGE });
    };

    const onPageChange = (next: number) => {
        void setState({ page: next });
    };

    const onPageSizeChange = (next: number) => {
        void setState({ size: next, page: FIRST_PAGE });
    };

    return {
        messages,
        total,
        hasMessages,
        mineOnly,
        statusValue,
        statusOptions,
        page,
        pageSize,
        isPending,
        isAdmin,
        onMineChange,
        onStatusChange,
        onPageChange,
        onPageSizeChange,
    };
};
