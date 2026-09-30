import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatCount, formatUsd } from "@/utils/format.utils";
import EstimatePanel from "./EstimatePanel";
import LocationPicker from "./LocationPicker";
import { useNewRun } from "./NewRun.Container";

const NewRun = () => {
    const run = useNewRun();

    if (run.isProfilesLoading) return <Loading />;

    if (run.profiles.length === 0) {
        return (
            <div className="space-y-4">
                <PageHeader title="New run" />
                <p className="text-sm text-muted-foreground">
                    There is no profile to search with yet. Set one up first (an industry such as solar).
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link to={APP_ROUTES.RUNS}>
                    <ArrowLeft />
                    All runs
                </Link>
            </Button>

            <PageHeader
                title="New run"
                description="Choose what to look for and where. The panel on the right shows the effort and cost before anything starts."
            />

            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>What to look for</CardTitle>
                            <CardDescription>The profile decides which searches are made.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-5">
                            {run.profiles.length > 1 && (
                                <div className="space-y-1.5">
                                    <Label htmlFor="run-profile">Profile</Label>
                                    <Select
                                        value={String(run.profileId)}
                                        onValueChange={(value) => run.setProfileId(Number(value))}
                                    >
                                        <SelectTrigger id="run-profile" className="w-full sm:w-72">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {run.profiles.map((profile) => (
                                                <SelectItem key={profile.id} value={String(profile.id)}>
                                                    {profile.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}

                            <fieldset className="space-y-2">
                                <legend className="text-sm font-medium">Kinds of business</legend>
                                <div className="grid gap-2 sm:grid-cols-2">
                                    {run.segments.map((segment) => (
                                        <div key={segment.id} className="flex items-start gap-2">
                                            <Checkbox
                                                id={`segment-${segment.id}`}
                                                className="mt-0.5"
                                                checked={run.segmentSlugs.includes(segment.slug)}
                                                onCheckedChange={() => run.toggleSegment(segment.slug)}
                                            />
                                            <Label htmlFor={`segment-${segment.id}`} className="block font-normal">
                                                <span className="font-medium">{segment.name}</span>
                                                {segment.description && (
                                                    <span className="block text-xs text-muted-foreground">
                                                        {segment.description}
                                                    </span>
                                                )}
                                            </Label>
                                        </div>
                                    ))}
                                </div>
                            </fieldset>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Where</CardTitle>
                            <CardDescription>Each city is searched separately.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <LocationPicker
                                tree={run.geographyTree}
                                selected={run.cityIds}
                                onChange={run.setCityIds}
                            />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Sources and options</CardTitle>
                            <CardDescription>Where to look, and what to do with what is found.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-5">
                            <fieldset className="space-y-3">
                                <legend className="sr-only">Sources</legend>
                                {run.discoverySources.map((source) => (
                                    <div key={source.key} className="flex items-start gap-2">
                                        <Checkbox
                                            id={`source-${source.key}`}
                                            className="mt-0.5"
                                            disabled={!source.is_available}
                                            checked={run.sourceKeys.includes(source.key)}
                                            onCheckedChange={() => run.toggleSource(source.key)}
                                        />
                                        <Label htmlFor={`source-${source.key}`} className="block font-normal">
                                            <span className="font-medium">
                                                {source.name}
                                                {source.is_paid && (
                                                    <span className="ml-2 rounded bg-warning px-1.5 py-0.5 text-xs font-normal text-warning-foreground">
                                                        Paid
                                                    </span>
                                                )}
                                            </span>
                                            <span className="block text-xs text-muted-foreground">
                                                {source.is_available
                                                    ? source.description
                                                    : "Not available: switched off or missing its API key."}
                                            </span>
                                        </Label>
                                    </div>
                                ))}
                            </fieldset>

                            {run.usesPaidSource && (
                                <div className="space-y-1.5">
                                    <Label htmlFor="run-cap">Spending cap (billable requests)</Label>
                                    <Input
                                        id="run-cap"
                                        type="number"
                                        min={1}
                                        inputMode="numeric"
                                        placeholder="No cap"
                                        value={run.maxPaid}
                                        onChange={(event) => run.setMaxPaid(event.target.value)}
                                        className="w-full sm:w-48"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        The run stops asking the paid source once it has made this many requests.
                                    </p>
                                </div>
                            )}

                            <div className="flex items-start justify-between gap-4 border-t pt-4">
                                <div>
                                    <Label htmlFor="run-enrich">Read each business's website</Label>
                                    <p className="text-xs text-muted-foreground">
                                        {run.enrichmentAvailable
                                            ? "Looks for an email address, WhatsApp number and social pages."
                                            : "Switched off by an administrator."}
                                    </p>
                                </div>
                                <Switch
                                    id="run-enrich"
                                    checked={run.enrichWebsites && run.enrichmentAvailable}
                                    disabled={!run.enrichmentAvailable}
                                    onCheckedChange={run.setEnrichWebsites}
                                />
                            </div>

                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <Label htmlFor="run-refresh">Search again</Label>
                                    <p className="text-xs text-muted-foreground">
                                        Repeat searches that already finished in the last few days instead of skipping them.
                                    </p>
                                </div>
                                <Switch id="run-refresh" checked={run.refresh} onCheckedChange={run.setRefresh} />
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <EstimatePanel
                    hasSelection={run.hasSelection}
                    estimate={run.estimate}
                    isEstimating={run.isEstimating}
                    error={run.estimateError}
                    canStart={run.canStart}
                    isStarting={run.isStarting}
                    onStart={run.requestStart}
                />
            </div>

            <ConfirmationModal
                open={run.showConfirm}
                title="Start a run that costs money?"
                description={
                    run.estimate
                        ? `This run may make up to ${formatCount(run.estimate.paid_requests_max)} billable Google requests (about ${formatUsd(run.estimate.estimated_cost_usd)} at the configured rate). You can cancel it while it runs.`
                        : ""
                }
                confirmText="Start run"
                isLoading={run.isStarting}
                onConfirm={run.confirmStart}
                onClose={() => run.setShowConfirm(false)}
            />
        </div>
    );
};

export default NewRun;
