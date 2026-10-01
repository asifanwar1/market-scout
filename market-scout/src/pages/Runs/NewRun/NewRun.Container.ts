import { useState, type ChangeEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import type { TCreateRunBody } from "@/api/services/runs/runs.request.types";
import { useGetGeographyTree, useGetProfile, useGetProfiles, useGetSources } from "@/hooks/api/catalog.queries";
import { useCreateRun, useEstimateRun } from "@/hooks/api/runs.queries";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { getErrorMessage } from "@/lib/errorHandlerUtils";
import { showToast } from "@/lib/toast";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatCount, formatUsd } from "@/utils/format.utils";
import { SOURCE_KIND } from "@/constants/source.constants";
import { CITY_URL_PARAM, ESTIMATE_DEBOUNCE_MS, MIN_PAID_CAP, NULL_BODY_KEY } from "./NewRun.constants";

type TRunFormState = {
    profileId: number;
    cityIds: number[];
    sourceKeys: string[];
    segmentSlugs: string[];
    allSegmentsCount: number;
    enrichWebsites: boolean;
    refresh: boolean;
    maxPaid: number;
    usesPaidSource: boolean;
};

const buildRunPayload = (form: TRunFormState): TCreateRunBody => ({
    profile_id: form.profileId,
    geography_ids: form.cityIds,
    source_keys: form.sourceKeys,
    segment_slugs: form.segmentSlugs.length === form.allSegmentsCount ? null : form.segmentSlugs,
    enrich_websites: form.enrichWebsites,
    refresh: form.refresh,
    max_paid_requests: form.usesPaidSource && form.maxPaid >= MIN_PAID_CAP ? Math.floor(form.maxPaid) : null,
});

const toggleItem = (list: string[], value: string): string[] =>
    list.includes(value) ? list.filter((item) => item !== value) : [...list, value];

export const useNewRun = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    const { data: profilesData, isPending: isProfilesLoading } = useGetProfiles();
    const profiles = profilesData?.data ?? [];
    const [chosenProfileId, setChosenProfileId] = useState<number | null>(null);
    const profileId = chosenProfileId ?? profiles[0]?.id;
    const { data: profile } = useGetProfile(profileId);
    const segments = profile?.segments ?? [];

    const { data: geographyTree = [] } = useGetGeographyTree();
    const { data: sourcesData } = useGetSources();
    const discoverySources = (sourcesData?.data ?? []).filter((source) => source.kind === SOURCE_KIND.DISCOVERY);
    const enrichmentSource = (sourcesData?.data ?? []).find((source) => source.kind === SOURCE_KIND.ENRICHMENT);

    const [chosenSegments, setChosenSegments] = useState<string[] | null>(null);
    const [chosenSources, setChosenSources] = useState<string[] | null>(null);
    const [cityIds, setCityIds] = useState<number[]>(() =>
        searchParams
            .getAll(CITY_URL_PARAM)
            .map(Number)
            .filter((id) => Number.isInteger(id) && id > 0),
    );
    const [enrichWebsites, setEnrichWebsites] = useState(true);
    const [refresh, setRefresh] = useState(false);
    const [maxPaid, setMaxPaid] = useState("");
    const [showConfirm, setShowConfirm] = useState(false);

    const sourceKeys =
        chosenSources ??
        discoverySources.filter((source) => source.is_available && !source.is_paid).map((source) => source.key);
    const segmentSlugs = chosenSegments ?? segments.map((segment) => segment.slug);
    const usesPaidSource = discoverySources.some((source) => source.is_paid && sourceKeys.includes(source.key));
    const enrichmentAvailable = enrichmentSource?.is_available ?? false;

    const hasSelection = Boolean(profileId) && cityIds.length > 0 && sourceKeys.length > 0 && segmentSlugs.length > 0;
    const body: TCreateRunBody | null =
        hasSelection && profileId
            ? buildRunPayload({
                  profileId,
                  cityIds,
                  sourceKeys,
                  segmentSlugs,
                  allSegmentsCount: segments.length,
                  enrichWebsites: enrichWebsites && enrichmentAvailable,
                  refresh,
                  maxPaid: Number(maxPaid),
                  usesPaidSource,
              })
            : null;

    const bodyKey = JSON.stringify(body);
    const settledKey = useDebouncedValue(bodyKey, ESTIMATE_DEBOUNCE_MS);
    const estimateQuery = useEstimateRun(settledKey === NULL_BODY_KEY ? null : (JSON.parse(settledKey) as TCreateRunBody));
    const estimate = estimateQuery.data;
    const isSettled = settledKey === bodyKey;

    const { mutateAsync: createRun, isPending: isStarting } = useCreateRun();

    const canStart =
        body !== null &&
        isSettled &&
        !estimateQuery.isFetching &&
        !estimateQuery.isError &&
        !!estimate?.allowed &&
        (estimate?.tasks_total ?? 0) > 0;

    const confirmStart = async () => {
        if (!body) return;
        const run = await createRun(body);
        showToast.success(`Run #${run.id} started`);
        navigate(APP_ROUTES.RUNS_DETAILS.replace(":id", String(run.id)));
    };

    const requestStart = () => {
        if ((estimate?.paid_requests_max ?? 0) > 0) {
            setShowConfirm(true);
            return;
        }
        void confirmStart();
    };

    const isEstimating = estimateQuery.isFetching || !isSettled;
    const estimateError = estimateQuery.isError ? getErrorMessage(estimateQuery.error) : null;

    const setProfileId = (id: number) => {
        setChosenProfileId(id);
        setChosenSegments(null);
    };

    const toggleSegment = (slug: string) => {
        setChosenSegments(toggleItem(segmentSlugs, slug));
    };

    const toggleSource = (key: string) => {
        setChosenSources(toggleItem(sourceKeys, key));
    };

    const onProfileChange = (value: string) => {
        setProfileId(Number(value));
    };

    const onMaxPaidChange = (event: ChangeEvent<HTMLInputElement>) => {
        setMaxPaid(event.target.value);
    };

    const hasMultipleProfiles = profiles.length > 1;
    const hasNoProfiles = profiles.length === 0;
    const profileValue = String(profileId);
    const isEnrichmentOn = enrichWebsites && enrichmentAvailable;
    const confirmDescription = estimate
        ? `This run may make up to ${formatCount(estimate.paid_requests_max)} billable Google requests (about ${formatUsd(estimate.estimated_cost_usd)} at the configured rate). You can cancel it while it runs.`
        : "";

    const closeConfirm = () => {
        setShowConfirm(false);
    };

    return {
        profiles,
        hasMultipleProfiles,
        hasNoProfiles,
        isProfilesLoading,
        profileId,
        profileValue,
        onProfileChange,
        segments,
        segmentSlugs,
        toggleSegment,
        geographyTree,
        cityIds,
        setCityIds,
        discoverySources,
        sourceKeys,
        toggleSource,
        usesPaidSource,
        enrichmentAvailable,
        enrichWebsites,
        setEnrichWebsites,
        refresh,
        setRefresh,
        maxPaid,
        onMaxPaidChange,
        isEnrichmentOn,
        confirmDescription,
        estimate,
        isEstimating,
        estimateError,
        hasSelection,
        canStart,
        isStarting,
        requestStart,
        confirmStart,
        showConfirm,
        closeConfirm,
    };
};
