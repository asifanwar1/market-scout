import type { ColumnDef } from "@tanstack/react-table";
import { Plus, Search, ShieldCheck, Undo2 } from "lucide-react";

import type { TDoNotContactResponse } from "@/api/services/businesses/businesses.response.types";
import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDate, formatPhone } from "@/utils/format.utils";
import AddDoNotContactDialog from "./AddDoNotContactDialog";
import { useDoNotContactPage } from "./DoNotContact.Container";

const KIND_LABELS = { business: "Business", phone: "Phone", email: "Email" } as const;

const DoNotContact = () => {
    const page = useDoNotContactPage();
    const { state, isAdmin, entries, total, isLoading, toLift, setToLift } = page;

    const columns: ColumnDef<TDoNotContactResponse, unknown>[] = [
        {
            id: "kind",
            header: "Type",
            enableSorting: false,
            cell: ({ row }) => <Badge variant="outline">{KIND_LABELS[row.original.kind]}</Badge>,
        },
        {
            id: "who",
            header: "Blocked",
            enableSorting: false,
            cell: ({ row }) => {
                const { kind, value, identifiers } = row.original;
                return (
                    <div className="min-w-0 max-w-80">
                        <p className="truncate font-medium">{kind === "phone" ? formatPhone(value) : value}</p>
                        {identifiers.length > 0 && (
                            <p className="truncate text-xs text-muted-foreground">
                                Also blocked: {identifiers.map((item) => (item.startsWith("+") ? formatPhone(item) : item)).join(", ")}
                            </p>
                        )}
                    </div>
                );
            },
        },
        {
            id: "reason",
            header: "Reason",
            enableSorting: false,
            cell: ({ row }) => (
                <span className="text-sm text-muted-foreground">{row.original.reason ?? "—"}</span>
            ),
        },
        {
            id: "added",
            header: "Added",
            enableSorting: false,
            cell: ({ row }) => (
                <span className="whitespace-nowrap text-sm text-muted-foreground">
                    {formatDate(row.original.created_at)}
                </span>
            ),
        },
        ...(isAdmin
            ? [
                  {
                      id: "actions",
                      header: "",
                      enableSorting: false,
                      size: 120,
                      cell: ({ row }) => (
                          <Button variant="ghost" size="sm" onClick={() => setToLift(row.original)}>
                              <Undo2 />
                              Lift block
                          </Button>
                      ),
                  } satisfies ColumnDef<TDoNotContactResponse, unknown>,
              ]
            : []),
    ];

    return (
        <div className="space-y-4">
            <PageHeader
                title="Do not contact"
                description="People and numbers that asked not to be contacted. They're hidden from Leads and skipped by every run."
                actions={
                    <Button onClick={() => page.setShowAdd(true)}>
                        <Plus />
                        Add phone or email
                    </Button>
                }
            />

            <div className="relative max-w-xs">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                    value={page.searchInput}
                    onChange={(event) => page.setSearchInput(event.target.value)}
                    placeholder="Search name, phone or email…"
                    aria-label="Search the do-not-contact list"
                    className="pl-8"
                />
            </div>

            <DataTable
                columns={columns}
                data={entries}
                getRowId={(entry) => String(entry.id)}
                isLoading={isLoading}
                emptyState={
                    <EmptyState
                        icon={ShieldCheck}
                        title={state.q ? "Nothing matches that search" : "Nobody is on the list"}
                        description={
                            state.q
                                ? undefined
                                : "When a business asks not to be contacted, mark it from its lead panel, or add a phone number or email here."
                        }
                    />
                }
            />

            {total > 0 && (
                <Pagination
                    page={state.page}
                    pageSize={state.size}
                    total={total}
                    onPageChange={page.setPage}
                    onPageSizeChange={page.setPageSize}
                />
            )}

            <AddDoNotContactDialog open={page.showAdd} onClose={() => page.setShowAdd(false)} />

            <ConfirmationModal
                open={toLift !== null}
                title="Lift this block?"
                description={
                    toLift?.kind === "business"
                        ? `${toLift.value} and its phone numbers and emails will appear in Leads again and can be updated by future runs.`
                        : "Whoever owns it can appear in Leads again and be added by future runs."
                }
                confirmText="Lift block"
                isLoading={page.isRemoving}
                onConfirm={page.confirmLift}
                onClose={() => setToLift(null)}
            />
        </div>
    );
};

export default DoNotContact;
