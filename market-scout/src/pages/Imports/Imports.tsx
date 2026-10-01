import { FileUp, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Button } from "@/components/ui/button";
import { APP_ROUTES } from "@/routes/appRoutes";
import { importColumns } from "./Imports.columns";
import { IMPORTS_EMPTY_DESCRIPTION, IMPORTS_PAGE_DESCRIPTION, IMPORTS_PAGE_TITLE } from "./Imports.constants";
import { useImportsPage } from "./Imports.Container";

const Imports = () => {
    const { imports, total, hasImports, page, pageSize, isPending, getImportRowId, openImport, onPageChange, onPageSizeChange } =
        useImportsPage();

    return (
        <div className="space-y-4">
            <PageHeader
                title={IMPORTS_PAGE_TITLE}
                description={IMPORTS_PAGE_DESCRIPTION}
                actions={
                    <Button asChild>
                        <Link to={APP_ROUTES.IMPORTS_NEW}>
                            <Plus />
                            New import
                        </Link>
                    </Button>
                }
            />

            <DataTable
                columns={importColumns}
                data={imports}
                getRowId={getImportRowId}
                isLoading={isPending}
                onRowClick={openImport}
                emptyState={
                    <EmptyState
                        icon={FileUp}
                        title="No imports yet"
                        description={IMPORTS_EMPTY_DESCRIPTION}
                        action={
                            <Button asChild>
                                <Link to={APP_ROUTES.IMPORTS_NEW}>Import a list</Link>
                            </Button>
                        }
                    />
                }
            />

            {hasImports && (
                <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
            )}
        </div>
    );
};

export default Imports;
