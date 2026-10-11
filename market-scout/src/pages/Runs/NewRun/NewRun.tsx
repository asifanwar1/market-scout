import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import type { TProfileListItem, TSegment } from "@/api/services/profiles/profiles.response.types";
import type { TSource } from "@/api/services/sources/sources.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { APP_ROUTES } from "@/routes/appRoutes";
import EstimatePanel from "./Components/EstimatePanel";
import LocationPicker from "./Components/LocationPicker";
import SegmentOption from "./Components/SegmentOption";
import SourceOption from "./Components/SourceOption";
import { NO_PROFILE_MESSAGE, PAID_CAP_REQUIRED_MESSAGE, REPEAT_HINT, SCHEDULE_NAME_MAX_LENGTH } from "./NewRun.constants";
import { useNewRun } from "./NewRun.Container";

const NewRun = () => {
    const {
        profiles,
        hasMultipleProfiles,
        hasNoProfiles,
        isProfilesLoading,
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
        setEnrichWebsites,
        refresh,
        setRefresh,
        maxPaid,
        onMaxPaidChange,
        isEnrichmentOn,
        confirmDescription,
        confirmTitle,
        confirmLabel,
        pageTitle,
        pageDescription,
        isRepeating,
        setIsRepeating,
        frequency,
        frequencyOptions,
        onFrequencyChange,
        scheduleName,
        onScheduleNameChange,
        needsPaidCap,
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
    } = useNewRun();

    const renderProfile = (profile: TProfileListItem) => (
        <SelectItem key={profile.id} value={String(profile.id)}>
            {profile.name}
        </SelectItem>
    );

    const renderSegment = (segment: TSegment) => (
        <SegmentOption key={segment.id} segment={segment} isChecked={segmentSlugs.includes(segment.slug)} onToggle={toggleSegment} />
    );

    const renderFrequency = (option: (typeof frequencyOptions)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );

    const renderSource = (source: TSource) => (
        <SourceOption key={source.key} source={source} isChecked={sourceKeys.includes(source.key)} onToggle={toggleSource} />
    );

    if (isProfilesLoading) return <Loading />;

    if (hasNoProfiles) {
        return (
            <div className="space-y-4">
                <PageHeader title={pageTitle} />
                <p className="text-sm text-muted-foreground">{NO_PROFILE_MESSAGE}</p>
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

            <PageHeader title={pageTitle} description={pageDescription} />

            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>What to look for</CardTitle>
                            <CardDescription>The profile decides which searches are made.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-5">
                            {hasMultipleProfiles && (
                                <div className="space-y-1.5">
                                    <Label htmlFor="run-profile">Profile</Label>
                                    <Select value={profileValue} onValueChange={onProfileChange}>
                                        <SelectTrigger id="run-profile" className="w-full sm:w-72">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>{profiles.map(renderProfile)}</SelectContent>
                                    </Select>
                                </div>
                            )}

                            <fieldset className="space-y-2">
                                <legend className="text-sm font-medium">Kinds of business</legend>
                                <div className="grid gap-2 sm:grid-cols-2">{segments.map(renderSegment)}</div>
                            </fieldset>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Where</CardTitle>
                            <CardDescription>Each city is searched separately.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <LocationPicker tree={geographyTree} selected={cityIds} onChange={setCityIds} />
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
                                {discoverySources.map(renderSource)}
                            </fieldset>

                            {usesPaidSource && (
                                <div className="space-y-1.5">
                                    <Label htmlFor="run-cap">Spending cap (billable requests)</Label>
                                    <Input
                                        id="run-cap"
                                        type="number"
                                        min={1}
                                        inputMode="numeric"
                                        placeholder="No cap"
                                        value={maxPaid}
                                        onChange={onMaxPaidChange}
                                        className="w-full sm:w-48"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        The run stops asking the paid source once it has made this many requests.
                                    </p>
                                    {needsPaidCap && (
                                        <p role="alert" className="text-xs text-destructive">
                                            {PAID_CAP_REQUIRED_MESSAGE}
                                        </p>
                                    )}
                                </div>
                            )}

                            <div className="flex items-start justify-between gap-4 border-t pt-4">
                                <div>
                                    <Label htmlFor="run-enrich">Read each business's website</Label>
                                    <p className="text-xs text-muted-foreground">
                                        {enrichmentAvailable
                                            ? "Looks for an email address, WhatsApp number and social pages."
                                            : "Switched off by an administrator."}
                                    </p>
                                </div>
                                <Switch id="run-enrich" checked={isEnrichmentOn} disabled={!enrichmentAvailable} onCheckedChange={setEnrichWebsites} />
                            </div>

                            {!isRepeating && (
                                <div className="flex items-start justify-between gap-4">
                                    <div>
                                        <Label htmlFor="run-refresh">Search again</Label>
                                        <p className="text-xs text-muted-foreground">
                                            Repeat searches that already finished in the last few days instead of skipping them.
                                        </p>
                                    </div>
                                    <Switch id="run-refresh" checked={refresh} onCheckedChange={setRefresh} />
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Repeat</CardTitle>
                            <CardDescription>Run this search again by itself, and add only what is new.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-5">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <Label htmlFor="run-repeat">Repeat this search</Label>
                                    <p className="text-xs text-muted-foreground">{REPEAT_HINT}</p>
                                </div>
                                <Switch id="run-repeat" checked={isRepeating} onCheckedChange={setIsRepeating} />
                            </div>

                            {isRepeating && (
                                <div className="grid gap-4 sm:grid-cols-2">
                                    <div className="space-y-1.5">
                                        <Label htmlFor="run-frequency">How often</Label>
                                        <Select value={frequency} onValueChange={onFrequencyChange}>
                                            <SelectTrigger id="run-frequency" className="w-full">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>{frequencyOptions.map(renderFrequency)}</SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label htmlFor="run-schedule-name">Name</Label>
                                        <Input
                                            id="run-schedule-name"
                                            value={scheduleName}
                                            maxLength={SCHEDULE_NAME_MAX_LENGTH}
                                            onChange={onScheduleNameChange}
                                        />
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                <EstimatePanel
                    hasSelection={hasSelection}
                    estimate={estimate}
                    isEstimating={isEstimating}
                    error={estimateError}
                    canStart={canStart}
                    isStarting={isStarting}
                    onStart={requestStart}
                    isRepeating={isRepeating}
                />
            </div>

            <ConfirmationModal
                open={showConfirm}
                title={confirmTitle}
                description={confirmDescription}
                confirmText={confirmLabel}
                isLoading={isStarting}
                onConfirm={confirmStart}
                onClose={closeConfirm}
            />
        </div>
    );
};

export default NewRun;
