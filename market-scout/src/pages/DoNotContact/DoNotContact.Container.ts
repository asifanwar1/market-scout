import { debounce, parseAsString, useQueryStates } from "nuqs";
import { useState, type ChangeEvent } from "react";

import type { TDoNotContactResponse } from "@/api/services/businesses/businesses.response.types";
import { FIRST_PAGE, SEARCH_DEBOUNCE_MS, USER_ROLE } from "@/constants";
import { useGetDoNotContact, useRemoveDoNotContact } from "@/hooks/api/compliance.queries";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { showToast } from "@/lib/toast";
import { useStore } from "@/store";
import { paginationUrlState } from "@/utils/listUrlState";
import {
    DO_NOT_CONTACT_KIND,
    EMPTY_LIST_DESCRIPTION,
    EMPTY_LIST_TITLE,
    LIFT_BUSINESS_DESCRIPTION_SUFFIX,
    LIFT_IDENTIFIER_DESCRIPTION,
    NO_SEARCH_MATCH_TITLE,
} from "./DoNotContact.constants";
import { getDoNotContactColumns } from "./DoNotContact.columns";

const urlState = {
    q: parseAsString.withDefault(""),
    ...paginationUrlState,
};

export const useDoNotContactPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const isAdmin = useStore((store) => store.user?.role === USER_ROLE.ADMIN);
    const search = useDebouncedValue(state.q, SEARCH_DEBOUNCE_MS);

    const { data, isPending } = useGetDoNotContact({
        search: search || undefined,
        page: state.page,
        limit: state.size,
    });
    const { mutateAsync: remove, isPending: isRemoving } = useRemoveDoNotContact();

    const [isAddOpen, setIsAddOpen] = useState(false);
    const [toLift, setToLift] = useState<TDoNotContactResponse | null>(null);

    const entries = data?.data ?? [];
    const total = data?.count ?? 0;
    const hasEntries = total > 0;
    const searchText = state.q;
    const hasSearch = state.q !== "";
    const page = state.page;
    const pageSize = state.size;
    const isLiftOpen = toLift !== null;
    const columns = getDoNotContactColumns(isAdmin, setToLift);
    const emptyTitle = hasSearch ? NO_SEARCH_MATCH_TITLE : EMPTY_LIST_TITLE;
    const emptyDescription = hasSearch ? undefined : EMPTY_LIST_DESCRIPTION;
    const liftDescription =
        toLift?.kind === DO_NOT_CONTACT_KIND.BUSINESS
            ? `${toLift.value} ${LIFT_BUSINESS_DESCRIPTION_SUFFIX}`
            : LIFT_IDENTIFIER_DESCRIPTION;

    const onSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
        void setState({ q: event.target.value || null, page: FIRST_PAGE }, { limitUrlUpdates: debounce(SEARCH_DEBOUNCE_MS) });
    };

    const onPageChange = (nextPage: number) => {
        void setState({ page: nextPage });
    };

    const onPageSizeChange = (size: number) => {
        void setState({ size, page: FIRST_PAGE });
    };

    const openAdd = () => {
        setIsAddOpen(true);
    };

    const closeAdd = () => {
        setIsAddOpen(false);
    };

    const cancelLift = () => {
        setToLift(null);
    };

    const getEntryRowId = (entry: TDoNotContactResponse) => String(entry.id);

    const confirmLift = async () => {
        if (!toLift) return;
        await remove(toLift.id);
        showToast.success(toLift.kind === DO_NOT_CONTACT_KIND.BUSINESS ? `${toLift.value} is back in Leads` : "Block lifted");
        setToLift(null);
    };

    return {
        columns,
        entries,
        total,
        hasEntries,
        searchText,
        page,
        pageSize,
        isPending,
        isRemoving,
        isAddOpen,
        isLiftOpen,
        emptyTitle,
        emptyDescription,
        liftDescription,
        onSearchChange,
        onPageChange,
        onPageSizeChange,
        openAdd,
        closeAdd,
        cancelLift,
        confirmLift,
        getEntryRowId,
    };
};
