import { debounce, parseAsString, parseAsStringLiteral, useQueryStates } from "nuqs";
import { useState, type ChangeEvent } from "react";

import type { UserModel } from "@/api/models/user.model";
import { ALL_OPTION_VALUE, FIRST_PAGE, SEARCH_DEBOUNCE_MS } from "@/constants";
import { useGetUsers } from "@/hooks/api/users.queries";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { paginationUrlState } from "@/utils/listUrlState";
import { USER_ROLE_FILTER_VALUES } from "./Users.constants";
import type { TUserRoleFilter } from "./Users.types";

const urlState = {
    q: parseAsString.withDefault(""),
    role: parseAsStringLiteral(USER_ROLE_FILTER_VALUES),
    ...paginationUrlState,
};

export const useUsersPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const search = useDebouncedValue(state.q, SEARCH_DEBOUNCE_MS);

    const { data, isPending } = useGetUsers({
        search: search || undefined,
        role: state.role ?? undefined,
        page: state.page,
        limit: state.size,
    });
    const users = data?.data ?? [];
    const total = data?.count ?? 0;
    const hasUsers = total > 0;

    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editing, setEditing] = useState<UserModel | null>(null);

    const onSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
        void setState({ q: event.target.value || null, page: FIRST_PAGE }, { limitUrlUpdates: debounce(SEARCH_DEBOUNCE_MS) });
    };

    const onRoleChange = (value: string) => {
        const role = value === ALL_OPTION_VALUE ? null : (value as TUserRoleFilter);
        void setState({ role, page: FIRST_PAGE });
    };

    const onPageChange = (page: number) => {
        void setState({ page });
    };

    const onPageSizeChange = (size: number) => {
        void setState({ size, page: FIRST_PAGE });
    };

    const openCreate = () => {
        setEditing(null);
        setIsDialogOpen(true);
    };

    const openEdit = (user: UserModel) => {
        setEditing(user);
        setIsDialogOpen(true);
    };

    const closeDialog = () => {
        setIsDialogOpen(false);
    };

    const getUserRowId = (user: UserModel) => String(user.id);

    const searchText = state.q;
    const roleFilter = state.role ?? ALL_OPTION_VALUE;
    const page = state.page;
    const pageSize = state.size;

    return {
        users,
        total,
        hasUsers,
        isPending,
        isDialogOpen,
        editing,
        searchText,
        roleFilter,
        page,
        pageSize,
        onSearchChange,
        onRoleChange,
        onPageChange,
        onPageSizeChange,
        openCreate,
        openEdit,
        closeDialog,
        getUserRowId,
    };
};
