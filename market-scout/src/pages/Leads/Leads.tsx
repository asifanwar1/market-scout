import ConfirmationModal from "@/components/custom/ConfirmationModal";
import DataTable from "@/components/custom/DataTable";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import BulkActionsBar from "./Components/BulkActionsBar";
import ExportMenu from "./Components/ExportMenu";
import LeadDrawer from "./Components/LeadDrawer";
import LeadsEmptyState from "./Components/LeadsEmptyState";
import LeadsFilters from "./Components/LeadsFilters";
import {
    BULK_DELETE_CONFIRM_TEXT,
    BULK_DELETE_TITLE,
    DELETE_LEAD_CONFIRM_TEXT,
    DELETE_LEAD_TITLE,
    LEADS_PAGE_DESCRIPTION,
    LEADS_PAGE_TITLE,
} from "./Leads.constants";
import { useLeadsPage } from "./Leads.Container";

const Leads = () => {
    const page = useLeadsPage();
    const {
        isAdmin,
        columns,
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
        isDeleteOpen,
        isDeleting,
        deleteDescription,
        cancelDelete,
        confirmDelete,
        isBulkDeleteOpen,
        isBulkDeleting,
        bulkDeleteDescription,
        cancelBulkDelete,
        confirmBulkDelete,
    } = page;

    return (
        <div className="space-y-4">
            <PageHeader
                title={LEADS_PAGE_TITLE}
                description={LEADS_PAGE_DESCRIPTION}
                actions={<ExportMenu page={page} />}
            />

            <LeadsFilters page={page} />
            <BulkActionsBar page={page} />

            <div className={tableClassName}>
                <DataTable
                    columns={columns}
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

            <ConfirmationModal
                open={isDeleteOpen}
                title={DELETE_LEAD_TITLE}
                description={deleteDescription}
                confirmText={DELETE_LEAD_CONFIRM_TEXT}
                destructive
                isLoading={isDeleting}
                onConfirm={confirmDelete}
                onClose={cancelDelete}
            />

            <ConfirmationModal
                open={isBulkDeleteOpen}
                title={BULK_DELETE_TITLE}
                description={bulkDeleteDescription}
                confirmText={BULK_DELETE_CONFIRM_TEXT}
                destructive
                isLoading={isBulkDeleting}
                onConfirm={confirmBulkDelete}
                onClose={cancelBulkDelete}
            />
        </div>
    );
};

export default Leads;
