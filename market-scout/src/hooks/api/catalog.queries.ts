import { useQuery } from "@tanstack/react-query";

import {
    GEOGRAPHY_QUERY_KEYS,
    GetGeographyTree,
    GetProfile,
    GetProfiles,
    GetSources,
    PROFILE_QUERY_KEYS,
    SOURCE_QUERY_KEYS,
} from "@/api";
import { useStore } from "@/store";

// Reference data (profiles, locations, sources) changes rarely, so it is cached for longer.
const REFERENCE_STALE_TIME = 5 * 60 * 1000;

export const useGetProfiles = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [PROFILE_QUERY_KEYS.PROFILES],
        enabled: isAuthenticated,
        staleTime: REFERENCE_STALE_TIME,
        queryFn: () => GetProfiles({ limit: 100, is_active: true }),
    });
};

export const useGetProfile = (id?: number) => {
    return useQuery({
        queryKey: [PROFILE_QUERY_KEYS.PROFILE, id],
        enabled: !!id,
        staleTime: REFERENCE_STALE_TIME,
        queryFn: () => GetProfile({ id: id as number }),
    });
};

export const useGetGeographyTree = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [GEOGRAPHY_QUERY_KEYS.TREE],
        enabled: isAuthenticated,
        staleTime: REFERENCE_STALE_TIME,
        queryFn: GetGeographyTree,
    });
};

export const useGetSources = () => {
    const isAuthenticated = useStore((state) => state.isAuthenticated);

    return useQuery({
        queryKey: [SOURCE_QUERY_KEYS.SOURCES],
        enabled: isAuthenticated,
        staleTime: 30 * 1000,
        queryFn: GetSources,
    });
};
