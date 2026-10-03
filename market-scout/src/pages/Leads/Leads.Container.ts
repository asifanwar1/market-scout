import type { RowSelectionState, SortingState } from "@tanstack/react-table";
import {
    debounce,
    parseAsBoolean,
    parseAsInteger,
    parseAsString,
    parseAsStringLiteral,
    useQueryStates,
} from "nuqs";
import { useState, type ChangeEvent } from "react";

import { ExportLeadsCsv, ExportLeadsXlsx } from "@/api";
import type {
    TBusinessFilters,
    TBusinessSort,
    TGetBusinessesParams,
    TSortDirection,
} from "@/api/services/businesses/businesses.request.types";
import type { TBusinessListItem } from "@/api/services/businesses/businesses.response.types";
import { FIRST_PAGE, LEAD_STATUS, SEARCH_DEBOUNCE_MS, USER_ROLE } from "@/constants";
import { GENERIC_ERROR_MESSAGE } from "@/constants/Validation-messages.constants";
import type { LeadStatus } from "@/constants/lead-status.constants";
import { useBulkDeleteBusinesses, useBulkUpdateBusinesses, useDeleteBusiness, useGetAssignees, useGetBusinesses } from "@/hooks/api/businesses.queries";
import { useGetGeographyTree, useGetProfile, useGetProfiles } from "@/hooks/api/catalog.queries";
import { useGetSourcesQuality } from "@/hooks/api/insights.queries";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { showToast } from "@/lib/toast";
import { useStore } from "@/store";
import { getBlobErrorMessage, saveBlob, todayStamp } from "@/utils/download.utils";
import { pluralize } from "@/utils/format.utils";
import { paginationUrlState } from "@/utils/listUrlState";
import {
    BULK_DELETE_DESCRIPTION_SUFFIX,
    DELETE_LEAD_DESCRIPTION_SUFFIX,
    DIRECTION_VALUES,
    EMPTY_KIND,
    EXPORT_FILE_PREFIX,
    EXPORT_FORMAT,
    EXPORT_OPTIONS,
    LEAD_SORT,
    SORT_DIRECTION,
    SORT_VALUES,
    UNASSIGNED,
} from "./Leads.constants";
import { getLeadColumns } from "./LeadsTable.columns";
import type { TBulkChange, TEmptyKind, TExportFormat } from "./Leads.types";

const STATUSES = Object.values(LEAD_STATUS) as [LeadStatus, ...LeadStatus[]];

const urlState = {
    profile: parseAsInteger,
    segment: parseAsString,
    location: parseAsInteger,
    status: parseAsStringLiteral(STATUSES),
    assignee: parseAsString,
    q: parseAsString.withDefault(""),
    phone: parseAsBoolean,
    whatsapp: parseAsBoolean,
    email: parseAsBoolean,
    website: parseAsBoolean,
    minScore: parseAsInteger,
    source: parseAsString,
    sort: parseAsStringLiteral(SORT_VALUES),
    dir: parseAsStringLiteral(DIRECTION_VALUES),
    lead: parseAsInteger,
    ...paginationUrlState,
};

const defaultDirection = (sort: TBusinessSort): TSortDirection =>
    sort === LEAD_SORT.NAME ? SORT_DIRECTION.ASC : SORT_DIRECTION.DESC;

const CLEARED_FILTERS = {
    segment: null,
    location: null,
    status: null,
    assignee: null,
    q: null,
    phone: null,
    whatsapp: null,
    email: null,
    website: null,
    minScore: null,
    source: null,
};

export const useLeadsPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });
    const isAdmin = useStore((store) => store.user?.role === USER_ROLE.ADMIN);
    const search = useDebouncedValue(state.q, SEARCH_DEBOUNCE_MS);

    const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
    const [isExporting, setIsExporting] = useState(false);
    const [isBulkDeleteOpen, setIsBulkDeleteOpen] = useState(false);
    const [leadToDelete, setLeadToDelete] = useState<TBusinessListItem | null>(null);

    const { data: profilesData, isPending: isProfilesLoading } = useGetProfiles();
    const profiles = profilesData?.data ?? [];
    const activeProfileId = state.profile ?? profiles[0]?.id;
    const hasActiveProfile = activeProfileId !== undefined;

    const { data: profile } = useGetProfile(activeProfileId);
    const { data: geographyTree = [] } = useGetGeographyTree();
    const { data: assignees = [] } = useGetAssignees();
    const { data: sourceQuality } = useGetSourcesQuality(activeProfileId, hasActiveProfile);

    const sort: TBusinessSort = state.sort ?? LEAD_SORT.SCORE;
    const direction: TSortDirection = state.dir ?? defaultDirection(sort);

    const filters: TBusinessFilters = {
        profile_id: activeProfileId,
        segment: state.segment ?? undefined,
        geography_id: state.location ?? undefined,
        status: state.status ?? undefined,
        assigned_to_id: state.assignee && state.assignee !== UNASSIGNED ? Number(state.assignee) : undefined,
        unassigned: state.assignee === UNASSIGNED ? true : undefined,
        has_phone: state.phone ? true : undefined,
        whatsapp_likely: state.whatsapp ? true : undefined,
        has_email: state.email ? true : undefined,
        has_website: state.website ? true : undefined,
        min_score: state.minScore ?? undefined,
        source: state.source ?? undefined,
        search: search || undefined,
    };
    const params: TGetBusinessesParams = {
        ...filters,
        sort,
        direction,
        page: state.page,
        limit: state.size,
    };

    const { data, isPending, isFetching } = useGetBusinesses(params, hasActiveProfile);
    const { mutateAsync: bulkUpdate, isPending: isBulkUpdating } = useBulkUpdateBusinesses();
    const { mutateAsync: bulkDelete, isPending: isBulkDeleting } = useBulkDeleteBusinesses();
    const { mutateAsync: deleteBusiness, isPending: isDeleting } = useDeleteBusiness();

    const leads = data?.data ?? [];
    const columns = getLeadColumns(isAdmin, setLeadToDelete);
    const total = data?.count ?? 0;
    const hasLeads = total > 0;
    const sources = sourceQuality?.data ?? [];
    const isLeadsLoading = isPending || isProfilesLoading;
    const sorting: SortingState = [{ id: sort, desc: direction === SORT_DIRECTION.DESC }];
    const selectedIds = Object.keys(rowSelection)
        .filter((id) => rowSelection[id])
        .map(Number);
    const page = state.page;
    const pageSize = state.size;
    const leadId = state.lead;
    const searchText = state.q;
    const isExportDisabled = !hasLeads || isExporting;
    const isDeleteOpen = leadToDelete !== null;
    const deleteDescription = `${leadToDelete?.name ?? ""} ${DELETE_LEAD_DESCRIPTION_SUFFIX}`;
    const bulkDeleteDescription = `${pluralize(selectedIds.length, "selected lead", "selected leads")} ${BULK_DELETE_DESCRIPTION_SUFFIX}`;
    const tableClassName = isFetching && !isLeadsLoading ? "opacity-70 transition-opacity" : "transition-opacity";

    const activeFilterCount = [
        state.segment,
        state.location,
        state.status,
        state.assignee,
        state.q,
        state.phone,
        state.whatsapp,
        state.email,
        state.website,
        state.minScore,
        state.source,
    ].filter((value) => value !== null && value !== "" && value !== false).length;

    const hasActiveFilters = activeFilterCount > 0;
    const hasNoProfile = !isProfilesLoading && profiles.length === 0;
    const emptyKind: TEmptyKind = hasNoProfile ? EMPTY_KIND.NO_PROFILE : hasActiveFilters ? EMPTY_KIND.FILTERED : EMPTY_KIND.NONE;

    const changeFilters = (patch: Parameters<typeof setState>[0]) => {
        setRowSelection({});
        void setState({ ...(patch as object), page: FIRST_PAGE });
    };

    const onSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
        setRowSelection({});
        void setState({ q: event.target.value || null, page: FIRST_PAGE }, { limitUrlUpdates: debounce(SEARCH_DEBOUNCE_MS) });
    };

    const setPage = (nextPage: number) => {
        setRowSelection({});
        void setState({ page: nextPage });
    };

    const onPageSizeChange = (size: number) => {
        void setState({ size, page: FIRST_PAGE });
    };

    const onSortingChange = (updater: SortingState | ((old: SortingState) => SortingState)) => {
        const next = typeof updater === "function" ? updater(sorting) : updater;
        const column = next[0];
        if (!column) return;
        changeFilters({
            sort: column.id as TBusinessSort,
            dir: column.desc ? SORT_DIRECTION.DESC : SORT_DIRECTION.ASC,
        });
    };

    const clearFilters = () => {
        changeFilters(CLEARED_FILTERS);
    };

    const exportLeads = async (format: TExportFormat) => {
        const option = EXPORT_OPTIONS.find((candidate) => candidate.format === format) ?? EXPORT_OPTIONS[0];
        const download = format === EXPORT_FORMAT.XLSX ? ExportLeadsXlsx : ExportLeadsCsv;
        setIsExporting(true);
        try {
            const blob = await download({ ...filters, sort, direction });
            saveBlob(blob, `${EXPORT_FILE_PREFIX}${todayStamp()}${option.extension}`);
            showToast.success(`Exported ${pluralize(total, "lead", "leads")}`);
        } catch (error) {
            showToast.error(error instanceof Error ? await getBlobErrorMessage(error) : GENERIC_ERROR_MESSAGE);
        } finally {
            setIsExporting(false);
        }
    };

    const applyBulkUpdate = async (change: TBulkChange, label: string) => {
        const { updated } = await bulkUpdate({ business_ids: selectedIds, ...change });
        showToast.success(`${label}: ${pluralize(updated, "lead", "leads")} updated`);
        setRowSelection({});
    };

    const cancelDelete = () => {
        setLeadToDelete(null);
    };

    const confirmDelete = async () => {
        if (!leadToDelete) return;
        await deleteBusiness(leadToDelete.id);
        showToast.success(`${leadToDelete.name} deleted`);
        setRowSelection({});
        if (leadId === leadToDelete.id) void setState({ lead: null });
        setLeadToDelete(null);
    };

    const openBulkDelete = () => {
        setIsBulkDeleteOpen(true);
    };

    const cancelBulkDelete = () => {
        setIsBulkDeleteOpen(false);
    };

    const confirmBulkDelete = async () => {
        const { deleted } = await bulkDelete({ business_ids: selectedIds });
        showToast.success(`${pluralize(deleted, "lead", "leads")} deleted`);
        if (leadId !== null && selectedIds.includes(leadId)) void setState({ lead: null });
        setRowSelection({});
        setIsBulkDeleteOpen(false);
    };

    const getLeadRowId = (lead: TBusinessListItem) => String(lead.id);

    const openLeadRow = (lead: TBusinessListItem) => {
        void setState({ lead: lead.id }, { history: "push" });
    };

    const openLead = (id: number) => {
        void setState({ lead: id }, { history: "push" });
    };

    const closeLead = () => {
        void setState({ lead: null });
    };

    return {
        state,
        setState,
        isAdmin,
        searchText,
        onSearchChange,
        profiles,
        isProfilesLoading,
        activeProfileId,
        profile,
        geographyTree,
        assignees,
        sources,
        columns,
        leads,
        total,
        hasLeads,
        page,
        pageSize,
        leadId,
        isLeadsLoading,
        isFetching,
        tableClassName,
        sorting,
        onSortingChange,
        rowSelection,
        setRowSelection,
        selectedIds,
        activeFilterCount,
        hasActiveFilters,
        emptyKind,
        changeFilters,
        clearFilters,
        setPage,
        onPageSizeChange,
        applyBulkUpdate,
        isBulkUpdating,
        exportLeads,
        isExporting,
        isExportDisabled,
        isDeleteOpen,
        isDeleting,
        deleteDescription,
        cancelDelete,
        confirmDelete,
        isBulkDeleteOpen,
        isBulkDeleting,
        bulkDeleteDescription,
        openBulkDelete,
        cancelBulkDelete,
        confirmBulkDelete,
        getLeadRowId,
        openLeadRow,
        openLead,
        closeLead,
    };
};

export type TLeadsPage = ReturnType<typeof useLeadsPage>;
