import { Download, Loader2 } from "lucide-react";

import DataTable from "@/components/custom/DataTable";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Button } from "@/components/ui/button";
import BulkActionsBar from "./Components/BulkActionsBar";
import LeadDrawer from "./Components/LeadDrawer";
import LeadsEmptyState from "./Components/LeadsEmptyState";
import LeadsFilters from "./Components/LeadsFilters";
import { LEADS_PAGE_DESCRIPTION, LEADS_PAGE_TITLE } from "./Leads.constants";
import { useLeadsPage } from "./Leads.Container";
import { leadColumns } from "./LeadsTable.columns";

const Leads = () => {
    const page = useLeadsPage();
    const {
        isAdmin,
        leads,
        total,
        hasLeads,
        pageSize,
        leadId,
        isLeadsLoading,
        tableClassName,
        sorting,
        onSortingChange,
        rowSelection,
        setRowSelection,
        emptyKind,
        clearFilters,
        setPage,
        onPageSizeChange,
        closeLead,
        openLeadRow,
        getLeadRowId,
        exportLeads,
        isExporting,
        isExportDisabled,
    } = page;

    return (
        <div className="space-y-4">
            <PageHeader
                title={LEADS_PAGE_TITLE}
                description={LEADS_PAGE_DESCRIPTION}
                actions={
                    <Button variant="outline" onClick={exportLeads} disabled={isExportDisabled}>
                        {isExporting ? <Loader2 className="animate-spin" /> : <Download />}
                        Export CSV
                    </Button>
                }
            />

            <LeadsFilters page={page} />
            <BulkActionsBar page={page} />

            <div className={tableClassName}>
                <DataTable
                    columns={leadColumns}
                    data={leads}
                    getRowId={getLeadRowId}
                    isLoading={isLeadsLoading}
                    sorting={sorting}
                    onSortingChange={onSortingChange}
                    rowSelection={rowSelection}
                    onRowSelectionChange={setRowSelection}
                    onRowClick={openLeadRow}
                    emptyState={<LeadsEmptyState kind={emptyKind} isAdmin={isAdmin} onClearFilters={clearFilters} />}
                />
            </div>

            {hasLeads && (
                <Pagination
                    page={page.page}
                    pageSize={pageSize}
                    total={total}
                    onPageChange={setPage}
                    onPageSizeChange={onPageSizeChange}
                />
            )}

            <LeadDrawer leadId={leadId} onClose={closeLead} />
        </div>
    );
};

export default Leads;
