import { useNavigate } from "react-router-dom";

import type { TProfileListItem } from "@/api/services/profiles/profiles.response.types";
import { useGetAllProfiles } from "@/hooks/api/profiles.queries";
import { APP_ROUTES } from "@/routes/appRoutes";

export const useProfilesPage = () => {
    const navigate = useNavigate();
    const { data, isPending } = useGetAllProfiles();
    const profiles = data?.data ?? [];

    const getProfileRowId = (profile: TProfileListItem) => String(profile.id);

    const openProfile = (profile: TProfileListItem) => {
        navigate(APP_ROUTES.PROFILES_DETAILS.replace(":id", String(profile.id)));
    };

    return {
        profiles,
        isPending,
        getProfileRowId,
        openProfile,
    };
};
