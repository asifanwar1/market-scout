import { Plus, Search, UserCog } from "lucide-react";

import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ALL_OPTION_VALUE, USER_ROLE } from "@/constants";
import UserDialog from "./Components/UserDialog";
import { USERS_PAGE_DESCRIPTION, USERS_PAGE_TITLE } from "./Users.constants";
import { userColumns } from "./Users.columns";
import { useUsersPage } from "./Users.Container";

const Users = () => {
    const {
        users,
        total,
        hasUsers,
        isPending,
        isDialogOpen,
        editing,
        searchText,
        roleFilter,
        page,
        pageSize,
        onSearchChange,
        onRoleChange,
        onPageChange,
        onPageSizeChange,
        openCreate,
        openEdit,
        closeDialog,
        getUserRowId,
    } = useUsersPage();

    return (
        <div className="space-y-4">
            <PageHeader
                title={USERS_PAGE_TITLE}
                description={USERS_PAGE_DESCRIPTION}
                actions={
                    <Button onClick={openCreate}>
                        <Plus />
                        New user
                    </Button>
                }
            />

            <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-56 max-w-xs flex-1">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        value={searchText}
                        onChange={onSearchChange}
                        placeholder="Search name or email…"
                        aria-label="Search users"
                        className="pl-8"
                    />
                </div>
                <Select value={roleFilter} onValueChange={onRoleChange}>
                    <SelectTrigger className="w-40" aria-label="Filter by role">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL_OPTION_VALUE}>All roles</SelectItem>
                        <SelectItem value={USER_ROLE.ADMIN}>Admins</SelectItem>
                        <SelectItem value={USER_ROLE.SALES}>Sales</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            <DataTable
                columns={userColumns}
                data={users}
                getRowId={getUserRowId}
                isLoading={isPending}
                onRowClick={openEdit}
                emptyState={<EmptyState icon={UserCog} title="No users match" description="Try a different search or role." />}
            />

            {hasUsers && (
                <Pagination
                    page={page}
                    pageSize={pageSize}
                    total={total}
                    onPageChange={onPageChange}
                    onPageSizeChange={onPageSizeChange}
                />
            )}

            <UserDialog open={isDialogOpen} user={editing} onClose={closeDialog} />
        </div>
    );
};

export default Users;
