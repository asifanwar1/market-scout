import { parseAsInteger, useQueryState } from "nuqs";
import { useState } from "react";

import { USER_ROLE } from "@/constants";
import { useGetProfiles } from "@/hooks/api/catalog.queries";
import {
    useGetCoverage,
    useGetGaps,
    useGetMovers,
    useGetOverview,
    useGetSourcesQuality,
    useGetTimeline,
} from "@/hooks/api/insights.queries";
import { useStore } from "@/store";
import {
    DEFAULT_GAP_THRESHOLD,
    DEFAULT_RANGE_INDEX,
    EMPTY_ADMIN_DESCRIPTION,
    EMPTY_SALES_DESCRIPTION,
    MOVERS_DAYS,
    PROFILE_URL_PARAM,
    RANGES,
} from "./Insights.constants";

export const useInsightsPage = () => {
    const isAdmin = useStore((state) => state.user?.role === USER_ROLE.ADMIN);
    const { data: profilesData, isPending: isProfilesLoading } = useGetProfiles();
    const profiles = profilesData?.data ?? [];

    const [chosenProfile, setChosenProfile] = useQueryState(PROFILE_URL_PARAM, parseAsInteger);
    const profileId = chosenProfile ?? profiles[0]?.id;

    const [rangeValue, setRangeValue] = useState(RANGES[DEFAULT_RANGE_INDEX].value);
    const range = RANGES.find((item) => item.value === rangeValue) ?? RANGES[DEFAULT_RANGE_INDEX];
    const [threshold, setThreshold] = useState(DEFAULT_GAP_THRESHOLD);

    const ready = profileId !== undefined;
    const overview = useGetOverview(profileId, ready);
    const coverage = useGetCoverage(profileId);
    const gaps = useGetGaps(profileId, threshold);
    const timeline = useGetTimeline(profileId, range.days, range.bucket, ready);
    const sources = useGetSourcesQuality(profileId, ready);
    const movers = useGetMovers(profileId, MOVERS_DAYS, ready);

    const hasProfile = profileId !== undefined;
    const hasProfileChoice = profiles.length > 1 && hasProfile;
    const isLoading = isProfilesLoading || (hasProfile && !overview.data);
    const isEmpty = overview.data?.total === 0 && !overview.isFetching;
    const emptyDescription = isAdmin ? EMPTY_ADMIN_DESCRIPTION : EMPTY_SALES_DESCRIPTION;
    const profileValue = String(profileId);

    const setProfileId = (id: number) => {
        void setChosenProfile(id);
    };

    const onProfileChange = (value: string) => {
        setProfileId(Number(value));
    };

    return {
        profiles,
        profileId,
        profileValue,
        hasProfile,
        hasProfileChoice,
        isAdmin,
        isLoading,
        isEmpty,
        emptyDescription,
        range,
        setRangeValue,
        threshold,
        setThreshold,
        overview,
        coverage,
        gaps,
        timeline,
        sources,
        movers,
        onProfileChange,
    };
};

export type TInsightsPage = ReturnType<typeof useInsightsPage>;
