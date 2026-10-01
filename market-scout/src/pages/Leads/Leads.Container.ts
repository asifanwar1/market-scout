import type { RowSelectionState, SortingState } from "@tanstack/react-table";
import {
    parseAsBoolean,
    parseAsInteger,
    parseAsString,
    parseAsStringLiteral,
    useQueryStates,
} from "nuqs";
import { useEffect, useMemo, useState } from "react";

import { ExportLeadsCsv } from "@/api";

import type {
    TBusinessFilters,
    TBusinessSort,
    TGetBusinessesParams,
    TSortDirection,
} from "@/api/services/businesses/businesses.request.types";
import Config from "@/Config";
import { LEAD_STATUS } from "@/constants";
import {
    useBulkUpdateBusinesses,
    useGetAssignees,
    useGetBusinesses,
} from "@/hooks/api/businesses.queries";
import {
    useGetGeographyTree,
    useGetProfile,
    useGetProfiles,
} from "@/hooks/api/catalog.queries";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { showToast } from "@/lib/toast";
import { getBlobErrorMessage, saveBlob, todayStamp } from "@/utils/download.utils";
import { pluralize } from "@/utils/format.utils";
import type { LeadStatus } from "@/constants/lead-status.constants";

const SORTS = ["score", "newest", "last_seen", "name"] as const;
const DIRECTIONS = ["asc", "desc"] as const;
const STATUSES = Object.values(LEAD_STATUS) as [LeadStatus, ...LeadStatus[]];

// Everything a user can change lives in the URL, so a filtered view can be bookmarked or
// sent to a colleague, and the back button behaves.
const urlState = {
    profile: parseAsInteger,
    segment: parseAsString,
    location: parseAsInteger,
    status: parseAsStringLiteral(STATUSES),
    // A user id, or "unassigned"
    assignee: parseAsString,
    q: parseAsString.withDefault(""),
    phone: parseAsBoolean,
    whatsapp: parseAsBoolean,
    email: parseAsBoolean,
    website: parseAsBoolean,
    minScore: parseAsInteger,
    sort: parseAsStringLiteral(SORTS),
    dir: parseAsStringLiteral(DIRECTIONS),
    page: parseAsInteger.withDefault(1),
    size: parseAsInteger.withDefault(Config.LIMIT),
    // The lead open in the side panel
    lead: parseAsInteger,
};

export const UNASSIGNED = "unassigned";
export const ALL = "all";

// Names sort A-Z; everything else newest / best first.
const defaultDirection = (sort: TBusinessSort): TSortDirection =>
    sort === "name" ? "asc" : "desc";

export const useLeadsPage = () => {
    const [state, setState] = useQueryStates(urlState, { history: "replace" });

    // The search box is typed into live but only hits the URL (and the server) once typing pauses.
    const [searchInput, setSearchInput] = useState(state.q);
    const debouncedSearch = useDebouncedValue(searchInput, 350);
    useEffect(() => {
        if (debouncedSearch !== state.q) {
            void setState({ q: debouncedSearch || null, page: 1 });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps -- only react to the debounced text
    }, [debouncedSearch]);

    const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

    const { data: profilesData, isPending: isProfilesLoading } = useGetProfiles();
    const profiles = profilesData?.data ?? [];
    const activeProfileId = state.profile ?? profiles[0]?.id;

    const { data: profile } = useGetProfile(activeProfileId);
    const { data: geographyTree } = useGetGeographyTree();
    const { data: assignees = [] } = useGetAssignees();

    const sort: TBusinessSort = state.sort ?? "score";
    const direction: TSortDirection = state.dir ?? defaultDirection(sort);

    const filters: TBusinessFilters = {
        profile_id: activeProfileId,
        segment: state.segment ?? undefined,
        geography_id: state.location ?? undefined,
        status: state.status ?? undefined,
        assigned_to_id:
            state.assignee && state.assignee !== UNASSIGNED
                ? Number(state.assignee)
                : undefined,
        unassigned: state.assignee === UNASSIGNED ? true : undefined,
        has_phone: state.phone ? true : undefined,
        whatsapp_likely: state.whatsapp ? true : undefined,
        has_email: state.email ? true : undefined,
        has_website: state.website ? true : undefined,
        min_score: state.minScore ?? undefined,
        search: state.q || undefined,
    };
    const params: TGetBusinessesParams = {
        ...filters,
        sort,
        direction,
        page: state.page,
        limit: state.size,
    };

    const {
        data,
        isPending: isLeadsLoading,
        isFetching,
    } = useGetBusinesses(params, activeProfileId !== undefined);

    const { mutateAsync: bulkUpdate, isPending: isBulkUpdating } =
        useBulkUpdateBusinesses();

    // Any change to what's shown starts over from page 1 with nothing selected.
    const changeFilters = (patch: Parameters<typeof setState>[0]) => {
        setRowSelection({});
        void setState({ ...(patch as object), page: 1 });
    };

    const setPage = (page: number) => {
        setRowSelection({});
        void setState({ page });
    };

    const sorting: SortingState = [{ id: sort, desc: direction === "desc" }];
    const onSortingChange = (updater: SortingState | ((old: SortingState) => SortingState)) => {
        const next = typeof updater === "function" ? updater(sorting) : updater;
        const column = next[0];
        if (!column) return;
        changeFilters({
            sort: column.id as TBusinessSort,
            dir: column.desc ? "desc" : "asc",
        });
    };

    const activeFilterCount = useMemo(
        () =>
            [
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
            ].filter((value) => value !== null && value !== "" && value !== false).length,
        [state],
    );

    const clearFilters = () => {
        setSearchInput("");
        changeFilters({
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
        });
    };

    // The file holds everything the current filters match, not just this page.
    const [isExporting, setIsExporting] = useState(false);
    const exportLeads = async () => {
        setIsExporting(true);
        try {
            const blob = await ExportLeadsCsv({ ...filters, sort, direction });
            saveBlob(blob, `market-scout-leads-${todayStamp()}.csv`);
            showToast.success(`Exported ${pluralize(data?.count ?? 0, "lead", "leads")}`);
        } catch (error) {
            showToast.error(await getBlobErrorMessage(error));
        } finally {
            setIsExporting(false);
        }
    };

    const selectedIds = Object.keys(rowSelection)
        .filter((id) => rowSelection[id])
        .map(Number);

    const applyBulkUpdate = async (
        change: { lead_status?: LeadStatus; assigned_to_id?: number | null },
        label: string,
    ) => {
        const { updated } = await bulkUpdate({ business_ids: selectedIds, ...change });
        showToast.success(`${label}: ${updated} lead${updated === 1 ? "" : "s"} updated`);
        setRowSelection({});
    };

    return {
        state,
        setState,
        searchInput,
        setSearchInput,
        profiles,
        isProfilesLoading,
        activeProfileId,
        profile,
        geographyTree: geographyTree ?? [],
        assignees,
        leads: data?.data ?? [],
        total: data?.count ?? 0,
        isLeadsLoading: isLeadsLoading || isProfilesLoading,
        isFetching,
        sorting,
        onSortingChange,
        rowSelection,
        setRowSelection,
        selectedIds,
        activeFilterCount,
        changeFilters,
        clearFilters,
        setPage,
        applyBulkUpdate,
        isBulkUpdating,
        exportLeads,
        isExporting,
        openLead: (id: number) => void setState({ lead: id }, { history: "push" }),
        closeLead: () => void setState({ lead: null }),
    };
};

export type TLeadsPage = ReturnType<typeof useLeadsPage>;
