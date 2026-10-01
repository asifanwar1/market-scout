import { AlertTriangle, ArrowLeft, Ban, Loader2, Users } from "lucide-react";
import { Link } from "react-router-dom";

import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import Stat from "@/components/custom/Stat";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { SKIP_REASON_LABELS, getImportStatus } from "@/constants/import-status.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatCount, formatDateTime, pluralize } from "@/utils/format.utils";
import { useImportDetails } from "./ImportDetails.Container";

const ImportDetails = () => {
    const { record, isLoading, isError, isActive, canCancel, showCancel, openCancel, closeCancel, handleCancel, isCancelling } = useImportDetails();

    if (isLoading) return <Loading />;
    if (isError || !record) {
        return (
            <div className="space-y-4">
                <p className="text-sm text-muted-foreground">This import couldn't be found.</p>
                <Button asChild variant="outline">
                    <Link to={APP_ROUTES.IMPORTS}>Back to imports</Link>
                </Button>
            </div>
        );
    }

    const status = getImportStatus(record.status);
    const stats = record.stats;
    const skippedTotal = Object.values(record.skipped).reduce((sum, count) => sum + count, 0);
    const leadsLink = `${APP_ROUTES.LEADS}?source=${encodeURIComponent(record.source_key)}`;

    const renderSkipReason = ([reason, count]: [string, number]) => (
        <li key={reason}>
            {pluralize(count, "row", "rows")} {SKIP_REASON_LABELS[reason] ?? reason} and {count === 1 ? "was" : "were"} set aside.
        </li>
    );
    return (
        <div className="space-y-6">
            <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link to={APP_ROUTES.IMPORTS}>
                    <ArrowLeft />
                    All imports
                </Link>
            </Button>

            <PageHeader
                title={record.label}
                description={`${record.filename} · ${record.profile_name}`}
                actions={
                    <>
                        <StatusBadge label={status?.label ?? record.status} className={status?.className} />
                        {canCancel && (
                            <Button variant="outline" onClick={openCancel}>
                                <Ban />
                                Cancel
                            </Button>
                        )}
                        <Button asChild variant="outline">
                            <Link to={leadsLink}>
                                <Users />
                                View these leads
                            </Link>
                        </Button>
                    </>
                }
            />

            {record.error && (
                <div role="alert" className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
                    <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
                    <p>{record.error}</p>
                </div>
            )}

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        Progress
                        {isActive && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
                    </CardTitle>
                    <CardAction>
                        <span className="text-2xl font-semibold tabular-nums">{record.progress_percent}%</span>
                    </CardAction>
                </CardHeader>
                <CardContent className="space-y-5">
                    <Progress value={record.progress_percent} aria-label="Import progress" />
                    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                        <Stat label="Rows in the file" value={formatCount(record.rows_total)} />
                        <Stat label="Checked" value={`${formatCount(record.rows_done)} / ${formatCount(record.rows_to_import)}`} />
                        <Stat label="Set aside" value={formatCount(skippedTotal)} hint="not imported" />
                        <Stat label="Started" value={record.started_at ? formatDateTime(record.started_at) : "—"} />
                    </dl>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>What happened</CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                        <Stat label="New leads" value={formatCount(stats.new ?? 0)} hint="not in Market Scout before" />
                        <Stat label="Already known" value={formatCount(stats.merged ?? 0)} hint="matched an existing lead" />
                        <Stat label="Do not contact" value={formatCount(stats.blocked ?? 0)} hint="refused" />
                        <Stat label="Failed to store" value={formatCount(stats.errors ?? 0)} />
                    </dl>
                    <dl className="grid grid-cols-2 gap-4 border-t pt-4 sm:grid-cols-4">
                        <Stat label="With a phone" value={formatCount(stats.with_phone ?? 0)} />
                        <Stat label="With an email" value={formatCount(stats.with_email ?? 0)} />
                        <Stat label="With a website" value={formatCount(stats.with_website ?? 0)} />
                        <Stat label="No city found" value={formatCount(stats.no_city ?? 0)} hint="filed without a city" />
                    </dl>

                    {record.lookup_contacts && (
                        <p className="border-t pt-4 text-sm text-muted-foreground">
                            {pluralize(stats.looked_up ?? 0, "row got its contact details", "rows got their contact details")} from Overture Maps (same name, same
                            city, and no other business with that name there). Those leads show Overture as a source.
                        </p>
                    )}

                    {(stats.shared_phones ?? 0) > 0 && (
                        <p className="border-t pt-4 text-sm text-muted-foreground">
                            {pluralize(stats.shared_phones, "phone number appears", "phone numbers appear")} on several unrelated companies (often an agent's or
                            consultant's line). {stats.shared_phones === 1 ? "It is" : "They are"} kept on each lead but never used to decide that two companies are the same one.
                        </p>
                    )}

                    {skippedTotal > 0 && (
                        <ul className="space-y-1 border-t pt-4 text-sm text-muted-foreground">
                            {Object.entries(record.skipped).map(renderSkipReason)}
                        </ul>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Settings used</CardTitle>
                </CardHeader>
                <CardContent>
                    <dl className="grid gap-4 text-sm sm:grid-cols-2">
                        <div>
                            <dt className="text-xs text-muted-foreground">Business type</dt>
                            <dd>{record.segment_slug ? `Every row is: ${record.segment_slug}` : "Decided from each name"}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-muted-foreground">City when the file didn't say</dt>
                            <dd>{record.default_geography_name ?? "None (filed without a city)"}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-muted-foreground">Rows with no contact details</dt>
                            <dd>{record.require_contact ? "Set aside" : "Kept"}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-muted-foreground">Missing phones</dt>
                            <dd>{record.lookup_contacts ? "Looked up in Overture Maps" : "Left as they are"}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-muted-foreground">Found by (shown on each lead)</dt>
                            <dd>{record.label}</dd>
                        </div>
                    </dl>
                </CardContent>
            </Card>

            <ConfirmationModal
                open={showCancel}
                destructive
                title="Cancel this import?"
                description="It stops after the batch it is on. What it has already added is kept."
                confirmText="Cancel import"
                cancelText="Keep importing"
                isLoading={isCancelling}
                onConfirm={handleCancel}
                onClose={closeCancel}
            />
        </div>
    );
};

export default ImportDetails;
