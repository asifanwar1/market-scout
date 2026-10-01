import { BarChart3 } from "lucide-react";
import { Link } from "react-router-dom";

import type { TProfileListItem } from "@/api/services/profiles/profiles.response.types";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { APP_ROUTES } from "@/routes/appRoutes";
import CoverageMatrix from "./Components/CoverageMatrix";
import GapsCard from "./Components/GapsCard";
import GrowthChart from "./Components/GrowthChart";
import MoversCard from "./Components/MoversCard";
import OverviewCards from "./Components/OverviewCards";
import SourceQualityCard from "./Components/SourceQualityCard";
import { INSIGHTS_PAGE_DESCRIPTION, INSIGHTS_PAGE_TITLE } from "./Insights.constants";
import { useInsightsPage } from "./Insights.Container";

const Insights = () => {
    const page = useInsightsPage();
    const {
        profiles,
        profileValue,
        hasProfile,
        hasProfileChoice,
        isAdmin,
        isLoading,
        isEmpty,
        emptyDescription,
        overview,
        coverage,
        gaps,
        timeline,
        sources,
        movers,
        onProfileChange,
    } = page;

    const renderProfile = (profile: TProfileListItem) => (
        <SelectItem key={profile.id} value={String(profile.id)}>
            {profile.name}
        </SelectItem>
    );

    const profilePicker = hasProfileChoice ? (
        <Select value={profileValue} onValueChange={onProfileChange}>
            <SelectTrigger className="w-52" aria-label="Profile">
                <SelectValue />
            </SelectTrigger>
            <SelectContent>{profiles.map(renderProfile)}</SelectContent>
        </Select>
    ) : undefined;

    const startRunAction = isAdmin ? (
        <Button asChild>
            <Link to={APP_ROUTES.RUNS_NEW}>Start a run</Link>
        </Button>
    ) : undefined;

    if (isLoading) {
        return (
            <div className="space-y-6">
                <PageHeader title={INSIGHTS_PAGE_TITLE} description={INSIGHTS_PAGE_DESCRIPTION} actions={profilePicker} />
                <Loading />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <PageHeader title={INSIGHTS_PAGE_TITLE} description={INSIGHTS_PAGE_DESCRIPTION} actions={profilePicker} />

            {!hasProfile ? (
                <EmptyState
                    icon={BarChart3}
                    title="No profile to report on yet"
                    description="Insights are organised by profile (an industry such as solar). An administrator needs to set one up first."
                />
            ) : (
                <>
                    {overview.data && <OverviewCards overview={overview.data} />}

                    {isEmpty && <EmptyState icon={BarChart3} title="No leads yet" description={emptyDescription} action={startRunAction} />}

                    <GrowthChart page={page} timeline={timeline.data} />
                    <div className="grid gap-6 xl:grid-cols-2">
                        <GapsCard page={page} gaps={gaps.data} />
                        <MoversCard movers={movers.data} />
                    </div>
                    <CoverageMatrix coverage={coverage.data} />
                    <SourceQualityCard sources={sources.data} />
                </>
            )}
        </div>
    );
};

export default Insights;
