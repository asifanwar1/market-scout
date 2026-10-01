import { parseAsInteger, useQueryStates } from "nuqs";

import Config from "@/Config";
import { useGetImports } from "@/hooks/api/imports.queries";

const urlState = {
    page: parseAsInteger.withDefault(1),
    size: parseAsInteger.withDefault(Config.LIMIT),
};

export const useImportsPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });

    const { data, isPending } = useGetImports({ page: state.page, limit: state.size });

    return {
        state,
        imports: data?.data ?? [],
        total: data?.count ?? 0,
        isLoading: isPending,
        setPage: (page: number) => void setState({ page }),
        setPageSize: (size: number) => void setState({ size, page: 1 }),
    };
};
