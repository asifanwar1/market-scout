import { Layers, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import DataTable from "@/components/custom/DataTable";
import EmptyState from "@/components/custom/EmptyState";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { APP_ROUTES } from "@/routes/appRoutes";
import { profileColumns } from "./Profiles.columns";
import { PROFILES_PAGE_DESCRIPTION, PROFILES_PAGE_TITLE, PROFILES_SKELETON_ROWS } from "./Profiles.constants";
import { useProfilesPage } from "./Profiles.Container";

const Profiles = () => {
    const { profiles, isPending, getProfileRowId, openProfile } = useProfilesPage();

    return (
        <div className="space-y-4">
            <PageHeader
                title={PROFILES_PAGE_TITLE}
                description={PROFILES_PAGE_DESCRIPTION}
                actions={
                    <Button asChild>
                        <Link to={APP_ROUTES.PROFILES_NEW}>
                            <Plus />
                            New profile
                        </Link>
                    </Button>
                }
            />

            <DataTable
                columns={profileColumns}
                data={profiles}
                getRowId={getProfileRowId}
                isLoading={isPending}
                skeletonRows={PROFILES_SKELETON_ROWS}
                onRowClick={openProfile}
                emptyState={
                    <EmptyState
                        icon={Layers}
                        title="No profiles yet"
                        description="Create one to describe what to look for, or run `python -m scripts.seed` on the server for the solar profile."
                    />
                }
            />
        </div>
    );
};

export default Profiles;
