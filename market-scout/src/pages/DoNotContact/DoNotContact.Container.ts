import { parseAsInteger, parseAsString, useQueryStates } from "nuqs";
import { useEffect, useState } from "react";

import type { TDoNotContactResponse } from "@/api/services/businesses/businesses.response.types";
import { USER_ROLE } from "@/constants";
import { useGetDoNotContact, useRemoveDoNotContact } from "@/hooks/api/compliance.queries";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { showToast } from "@/lib/toast";
import { useStore } from "@/store";

const urlState = {
    q: parseAsString.withDefault(""),
    page: parseAsInteger.withDefault(1),
    size: parseAsInteger.withDefault(25),
};

export const useDoNotContactPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const isAdmin = useStore((store) => store.user?.role === USER_ROLE.ADMIN);

    const [searchInput, setSearchInput] = useState(state.q);
    const debouncedSearch = useDebouncedValue(searchInput, 350);
    useEffect(() => {
        if (debouncedSearch !== state.q) void setState({ q: debouncedSearch || null, page: 1 });
        // eslint-disable-next-line react-hooks/exhaustive-deps -- only react to the debounced text
    }, [debouncedSearch]);

    const { data, isPending } = useGetDoNotContact({
        search: state.q || undefined,
        page: state.page,
        limit: state.size,
    });
    const { mutateAsync: remove, isPending: isRemoving } = useRemoveDoNotContact();

    const [showAdd, setShowAdd] = useState(false);
    const [toLift, setToLift] = useState<TDoNotContactResponse | null>(null);

    const confirmLift = async () => {
        if (!toLift) return;
        await remove(toLift.id);
        showToast.success(
            toLift.kind === "business" ? `${toLift.value} is back in Leads` : "Block lifted",
        );
        setToLift(null);
    };

    return {
        state,
        isAdmin,
        searchInput,
        setSearchInput,
        entries: data?.data ?? [],
        total: data?.count ?? 0,
        isLoading: isPending,
        showAdd,
        setShowAdd,
        toLift,
        setToLift,
        confirmLift,
        isRemoving,
        setPage: (page: number) => void setState({ page }),
        setPageSize: (size: number) => void setState({ size, page: 1 }),
    };
};
