import { parseAsBoolean, parseAsStringLiteral, useQueryStates } from "nuqs";

import type { TAlert } from "@/api/services/alerts/alerts.response.types";
import { ALERT_KIND_OPTIONS } from "@/constants/alert.constants";
import { ALL_OPTION_VALUE, FIRST_PAGE } from "@/constants";
import { USER_ROLE } from "@/constants/user-role.constants";
import { useGetAlerts, useMarkAlertsRead } from "@/hooks/api/alerts.queries";
import { showToast } from "@/lib/toast";
import { useStore } from "@/store";
import { paginationUrlState } from "@/utils/listUrlState";
import { ALERTS_EMPTY_TITLE, ALERTS_EMPTY_UNREAD_TITLE, ALERT_KIND_FILTER_VALUES } from "./Alerts.constants";

const urlState = {
    unread: parseAsBoolean.withDefault(false),
    kind: parseAsStringLiteral(ALERT_KIND_FILTER_VALUES),
    ...paginationUrlState,
};

export const useAlertsPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const user = useStore((store) => store.user);

    const { data, isPending } = useGetAlerts({
        unread_only: state.unread || undefined,
        kind: state.kind ?? undefined,
        page: state.page,
        limit: state.size,
    });
    const { mutateAsync: markRead, isPending: isMarking } = useMarkAlertsRead();

    const alerts = data?.data ?? [];
    const total = data?.count ?? 0;
    const unreadCount = data?.unread ?? 0;
    const hasAlerts = total > 0;
    const unreadOnly = state.unread;
    const kindValue = state.kind ?? ALL_OPTION_VALUE;
    const page = state.page;
    const pageSize = state.size;
    const kindOptions = ALERT_KIND_OPTIONS;
    const isAdmin = user?.role === USER_ROLE.ADMIN;
    const canMarkAll = unreadCount > 0 && !isMarking;
    const emptyTitle = unreadOnly ? ALERTS_EMPTY_UNREAD_TITLE : ALERTS_EMPTY_TITLE;

    const onUnreadChange = (checked: boolean) => {
        void setState({ unread: checked || null, page: FIRST_PAGE });
    };

    const onKindChange = (value: string) => {
        const next = ALERT_KIND_FILTER_VALUES.find((candidate) => candidate === value) ?? null;
        void setState({ kind: next, page: FIRST_PAGE });
    };

    const onPageChange = (next: number) => {
        void setState({ page: next });
    };

    const onPageSizeChange = (next: number) => {
        void setState({ size: next, page: FIRST_PAGE });
    };

    const openAlert = (alert: TAlert) => {
        if (!alert.is_read) void markRead({ ids: [alert.id] });
    };

    const markAllRead = async () => {
        await markRead({ all: true });
        showToast.success("All alerts marked as read");
    };

    return {
        alerts,
        total,
        unreadCount,
        hasAlerts,
        unreadOnly,
        kindValue,
        kindOptions,
        page,
        pageSize,
        isPending,
        isAdmin,
        canMarkAll,
        emptyTitle,
        onUnreadChange,
        onKindChange,
        onPageChange,
        onPageSizeChange,
        openAlert,
        markAllRead,
    };
};
