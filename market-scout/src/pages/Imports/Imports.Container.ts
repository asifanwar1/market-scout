import { useQueryStates } from "nuqs";
import { useNavigate } from "react-router-dom";

import type { TImport } from "@/api/services/imports/imports.response.types";
import { FIRST_PAGE } from "@/constants";
import { useGetImports } from "@/hooks/api/imports.queries";
import { APP_ROUTES } from "@/routes/appRoutes";
import { paginationUrlState } from "@/utils/listUrlState";

export const useImportsPage = () => {
    const navigate = useNavigate();
    const [state, setState] = useQueryStates(paginationUrlState, { history: "replace" });

    const { data, isPending } = useGetImports({ page: state.page, limit: state.size });
    const imports = data?.data ?? [];
    const total = data?.count ?? 0;
    const hasImports = total > 0;
    const page = state.page;
    const pageSize = state.size;

    const getImportRowId = (item: TImport) => String(item.id);

    const openImport = (item: TImport) => {
        navigate(APP_ROUTES.IMPORTS_DETAILS.replace(":id", String(item.id)));
    };

    const onPageChange = (nextPage: number) => {
        void setState({ page: nextPage });
    };

    const onPageSizeChange = (size: number) => {
        void setState({ size, page: FIRST_PAGE });
    };

    return {
        imports,
        total,
        hasImports,
        page,
        pageSize,
        isPending,
        getImportRowId,
        openImport,
        onPageChange,
        onPageSizeChange,
    };
};
