import { Plus, Search, ShieldCheck } from "lucide-react";

import ConfirmationModal from "@/components/custom/ConfirmationModal";
import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import AddDoNotContactDialog from "./Components/AddDoNotContactDialog";
import { DO_NOT_CONTACT_PAGE_DESCRIPTION, DO_NOT_CONTACT_PAGE_TITLE } from "./DoNotContact.constants";
import { useDoNotContactPage } from "./DoNotContact.Container";

const DoNotContact = () => {
    const {
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
    } = useDoNotContactPage();

    return (
        <div className="space-y-4">
            <PageHeader
                title={DO_NOT_CONTACT_PAGE_TITLE}
                description={DO_NOT_CONTACT_PAGE_DESCRIPTION}
                actions={
                    <Button onClick={openAdd}>
                        <Plus />
                        Add phone or email
                    </Button>
                }
            />

            <div className="relative max-w-xs">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                    value={searchText}
                    onChange={onSearchChange}
                    placeholder="Search name, phone or email…"
                    aria-label="Search the do-not-contact list"
                    className="pl-8"
                />
            </div>

            <DataTable
                columns={columns}
                data={entries}
                getRowId={getEntryRowId}
                isLoading={isPending}
                emptyState={<EmptyState icon={ShieldCheck} title={emptyTitle} description={emptyDescription} />}
            />

            {hasEntries && (
                <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
            )}

            <AddDoNotContactDialog open={isAddOpen} onClose={closeAdd} />

            <ConfirmationModal
                open={isLiftOpen}
                title="Lift this block?"
                description={liftDescription}
                confirmText="Lift block"
                isLoading={isRemoving}
                onConfirm={confirmLift}
                onClose={cancelLift}
            />
        </div>
    );
};

export default DoNotContact;
