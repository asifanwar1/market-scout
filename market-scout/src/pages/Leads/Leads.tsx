import { Download, Loader2, Radar, SearchX, UserX } from "lucide-react";
import { Link } from "react-router-dom";

import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Button } from "@/components/ui/button";
import { USER_ROLE } from "@/constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store";
import BulkActionsBar from "./BulkActionsBar";
import LeadDrawer from "./LeadDrawer";
import { useLeadsPage } from "./Leads.Container";
import { leadColumns } from "./LeadsTable.columns";
import LeadsFilters from "./LeadsFilters";

const Leads = () => {
    const page = useLeadsPage();
    const isAdmin = useStore((state) => state.user?.role === USER_ROLE.ADMIN);
    const {
        state,
        setState,
        leads,
        total,
        isLeadsLoading,
        isFetching,
        sorting,
        onSortingChange,
        rowSelection,
        setRowSelection,
        activeFilterCount,
        clearFilters,
        setPage,
        openLead,
        closeLead,
        profiles,
        isProfilesLoading,
        exportLeads,
        isExporting,
    } = page;

    const emptyState = (() => {
        if (!isProfilesLoading && profiles.length === 0) {
            return (
                <EmptyState
                    icon={UserX}
                    title="No profile to search yet"
                    description="Leads are organised by profile (an industry such as solar). An administrator needs to set one up first."
                />
            );
        }
        if (activeFilterCount > 0) {
            return (
                <EmptyState
                    icon={SearchX}
                    title="No leads match these filters"
                    description="Try removing a filter or searching for something else."
                    action={
                        <Button variant="outline" onClick={clearFilters}>
                            Clear filters
                        </Button>
                    }
                />
            );
        }
        return (
            <EmptyState
                icon={Radar}
                title="No leads yet"
                description={
                    isAdmin
                        ? "Start a run to search for businesses in the cities you sell in."
                        : "Leads appear here once an administrator has run a search."
                }
                action={
                    isAdmin ? (
                        <Button asChild>
                            <Link to={APP_ROUTES.RUNS_NEW}>Start a run</Link>
                        </Button>
                    ) : undefined
                }
            />
        );
    })();

    return (
        <div className="space-y-4">
            <PageHeader
                title="Leads"
                description="Businesses to contact, best first. Click a row for details and to record what happened."
                actions={
                    <Button variant="outline" onClick={exportLeads} disabled={total === 0 || isExporting}>
                        {isExporting ? <Loader2 className="animate-spin" /> : <Download />}
                        Export CSV
                    </Button>
                }
            />

            <LeadsFilters page={page} />
            <BulkActionsBar page={page} />

            <div className={isFetching && !isLeadsLoading ? "opacity-70 transition-opacity" : "transition-opacity"}>
                <DataTable
                    columns={leadColumns}
                    data={leads}
                    getRowId={(lead) => String(lead.id)}
                    isLoading={isLeadsLoading}
                    sorting={sorting}
                    onSortingChange={onSortingChange}
                    rowSelection={rowSelection}
                    onRowSelectionChange={setRowSelection}
                    onRowClick={(lead) => openLead(lead.id)}
                    emptyState={emptyState}
                />
            </div>

            {total > 0 && (
                <Pagination
                    page={state.page}
                    pageSize={state.size}
                    total={total}
                    onPageChange={setPage}
                    onPageSizeChange={(size) => void setState({ size, page: 1 })}
                />
            )}

            <LeadDrawer leadId={state.lead} onClose={closeLead} />
        </div>
    );
};

export default Leads;
