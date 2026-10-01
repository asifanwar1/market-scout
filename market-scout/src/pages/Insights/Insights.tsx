import { BarChart3 } from "lucide-react";
import { Link } from "react-router-dom";

import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { USER_ROLE } from "@/constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store";
import CoverageMatrix from "./CoverageMatrix";
import GapsCard from "./GapsCard";
import GrowthChart from "./GrowthChart";
import { useInsightsPage } from "./Insights.Container";
import MoversCard from "./MoversCard";
import OverviewCards from "./OverviewCards";
import SourceQualityCard from "./SourceQualityCard";

const Insights = () => {
    const page = useInsightsPage();
    const isAdmin = useStore((state) => state.user?.role === USER_ROLE.ADMIN);
    const { profiles, isProfilesLoading, profileId, overview, coverage, gaps, timeline, sources, movers } = page;

    const isEmpty = overview.data?.total === 0 && !overview.isFetching;

    return (
        <div className="space-y-6">
            <PageHeader
                title="Insights"
                description="What the searches have found so far, where the market is still thin, and which source is pulling its weight."
                actions={
                    profiles.length > 1 && profileId !== undefined ? (
                        <Select value={String(profileId)} onValueChange={(value) => page.setProfileId(Number(value))}>
                            <SelectTrigger className="w-52" aria-label="Profile">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {profiles.map((profile) => (
                                    <SelectItem key={profile.id} value={String(profile.id)}>
                                        {profile.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    ) : undefined
                }
            />

            {isProfilesLoading || (profileId !== undefined && !overview.data) ? (
                <Loading />
            ) : profileId === undefined ? (
                <EmptyState
                    icon={BarChart3}
                    title="No profile to report on yet"
                    description="Insights are organised by profile (an industry such as solar). An administrator needs to set one up first."
                />
            ) : (
                <>
                    {overview.data && <OverviewCards overview={overview.data} />}

                    {isEmpty && (
                        <EmptyState
                            icon={BarChart3}
                            title="No leads yet"
                            description={isAdmin ? "Start a run and this page fills in with coverage, gaps and source quality." : "This page fills in once an administrator has run a search."}
                            action={
                                isAdmin ? (
                                    <Button asChild>
                                        <Link to={APP_ROUTES.RUNS_NEW}>Start a run</Link>
                                    </Button>
                                ) : undefined
                            }
                        />
                    )}

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
