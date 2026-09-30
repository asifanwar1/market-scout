import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { TCreateRunBody } from "@/api/services/runs/runs.request.types";
import { useGetGeographyTree, useGetProfile, useGetProfiles, useGetSources } from "@/hooks/api/catalog.queries";
import { useCreateRun, useEstimateRun } from "@/hooks/api/runs.queries";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { getErrorMessage } from "@/lib/errorHandlerUtils";
import { showToast } from "@/lib/toast";
import { APP_ROUTES } from "@/routes/appRoutes";

export const useNewRun = () => {
    const navigate = useNavigate();

    const { data: profilesData, isPending: isProfilesLoading } = useGetProfiles();
    const profiles = profilesData?.data ?? [];
    const [chosenProfileId, setChosenProfileId] = useState<number | null>(null);
    const profileId = chosenProfileId ?? profiles[0]?.id;
    const { data: profile } = useGetProfile(profileId);
    const segments = profile?.segments ?? [];

    const { data: geographyTree = [] } = useGetGeographyTree();
    const { data: sourcesData } = useGetSources();
    const discoverySources = (sourcesData?.data ?? []).filter((source) => source.kind === "discovery");
    const enrichmentSource = (sourcesData?.data ?? []).find((source) => source.kind === "enrichment");

    // null means "the default": every segment; the free sources that are switched on.
    const [chosenSegments, setChosenSegments] = useState<string[] | null>(null);
    const [chosenSources, setChosenSources] = useState<string[] | null>(null);
    const [cityIds, setCityIds] = useState<number[]>([]);
    const [enrichWebsites, setEnrichWebsites] = useState(true);
    const [refresh, setRefresh] = useState(false);
    const [maxPaid, setMaxPaid] = useState("");
    const [showConfirm, setShowConfirm] = useState(false);

    // Paid sources are never ticked for you: spending money should be a deliberate act.
    const sourceKeys =
        chosenSources ??
        discoverySources.filter((source) => source.is_available && !source.is_paid).map((source) => source.key);
    const segmentSlugs = chosenSegments ?? segments.map((segment) => segment.slug);
    const usesPaidSource = discoverySources.some((source) => source.is_paid && sourceKeys.includes(source.key));
    const enrichmentAvailable = enrichmentSource?.is_available ?? false;

    const cap = Number(maxPaid);
    const body: TCreateRunBody | null =
        profileId && cityIds.length > 0 && sourceKeys.length > 0 && segmentSlugs.length > 0
            ? {
                  profile_id: profileId,
                  geography_ids: cityIds,
                  source_keys: sourceKeys,
                  // Sending null (not the full list) lets a segment added to the profile later be picked up.
                  segment_slugs: segmentSlugs.length === segments.length ? null : segmentSlugs,
                  enrich_websites: enrichWebsites && enrichmentAvailable,
                  refresh,
                  max_paid_requests: usesPaidSource && cap >= 1 ? Math.floor(cap) : null,
              }
            : null;

    // The estimate is asked for once the user pauses, and a run can only start on an estimate
    // that matches exactly what is on screen.
    const bodyKey = JSON.stringify(body);
    const settledKey = useDebouncedValue(bodyKey, 400);
    const estimate = useEstimateRun(settledKey === "null" ? null : (JSON.parse(settledKey) as TCreateRunBody));
    const isSettled = settledKey === bodyKey;

    const { mutateAsync: createRun, isPending: isStarting } = useCreateRun();

    const canStart =
        body !== null &&
        isSettled &&
        !estimate.isFetching &&
        !estimate.isError &&
        !!estimate.data?.allowed &&
        (estimate.data?.tasks_total ?? 0) > 0;

    const start = async () => {
        if (!body) return;
        const run = await createRun(body);
        showToast.success(`Run #${run.id} started`);
        navigate(APP_ROUTES.RUNS_DETAILS.replace(":id", String(run.id)));
    };

    // A run that may spend money asks first; a free one just starts.
    const requestStart = () => {
        if ((estimate.data?.paid_requests_max ?? 0) > 0) {
            setShowConfirm(true);
            return;
        }
        void start();
    };

    const toggle = (list: string[], value: string) =>
        list.includes(value) ? list.filter((item) => item !== value) : [...list, value];

    return {
        profiles,
        isProfilesLoading,
        profileId,
        setProfileId: (id: number) => {
            setChosenProfileId(id);
            setChosenSegments(null);
        },
        segments,
        segmentSlugs,
        toggleSegment: (slug: string) => setChosenSegments(toggle(segmentSlugs, slug)),
        geographyTree,
        cityIds,
        setCityIds,
        discoverySources,
        sourceKeys,
        toggleSource: (key: string) => setChosenSources(toggle(sourceKeys, key)),
        usesPaidSource,
        enrichmentAvailable,
        enrichWebsites,
        setEnrichWebsites,
        refresh,
        setRefresh,
        maxPaid,
        setMaxPaid,
        estimate: estimate.data,
        isEstimating: estimate.isFetching || !isSettled,
        estimateError: estimate.isError ? getErrorMessage(estimate.error) : null,
        hasSelection: body !== null,
        canStart,
        isStarting,
        requestStart,
        confirmStart: start,
        showConfirm,
        setShowConfirm,
    };
};
