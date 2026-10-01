import { AlertTriangle, ExternalLink, Loader2, RefreshCw } from "lucide-react";

import type { TSheetsSettings } from "@/api/services/sheets/sheets.response.types";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime, formatRelative, pluralize } from "@/utils/format.utils";

type TSyncStatusCardProps = {
    settings: TSheetsSettings;
    isSyncing: boolean;
    onSync: () => void;
};

const badge = (settings: TSheetsSettings, isSyncing: boolean) => {
    if (isSyncing) return { label: "Updating…", className: "bg-muted text-muted-foreground" };
    if (!settings.is_configured) return { label: "Not connected", className: "bg-muted text-muted-foreground" };
    if (settings.last_sync_ok === false) return { label: "Last update failed", className: "bg-destructive/10 text-destructive" };
    if (settings.last_synced_at) return { label: "Up to date", className: "bg-success text-success-foreground" };
    return { label: "Connected", className: "bg-warning text-warning-foreground" };
};

const SyncStatusCard = ({ settings, isSyncing, onSync }: TSyncStatusCardProps) => {
    const status = badge(settings, isSyncing);

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    Live sheet
                    <StatusBadge label={status.label} className={status.className} />
                </CardTitle>
                <CardAction className="flex flex-wrap items-center gap-2">
                    {settings.spreadsheet_url && (
                        <Button asChild variant="outline">
                            <a href={settings.spreadsheet_url} target="_blank" rel="noopener noreferrer">
                                <ExternalLink />
                                Open sheet
                            </a>
                        </Button>
                    )}
                    <Button onClick={onSync} disabled={!settings.is_configured || isSyncing}>
                        {isSyncing ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                        Sync now
                    </Button>
                </CardAction>
            </CardHeader>
            <CardContent className="space-y-4">
                {settings.last_synced_at ? (
                    <p className="text-sm">
                        Last updated <span className="font-medium">{formatRelative(settings.last_synced_at)}</span>
                        <span className="text-muted-foreground">
                            {" "}
                            ({formatDateTime(settings.last_synced_at)}) · {pluralize(settings.last_row_count ?? 0, "lead", "leads")}
                        </span>
                    </p>
                ) : (
                    <p className="text-sm text-muted-foreground">
                        {settings.is_configured
                            ? "Connected, but not updated yet. Press Sync now to fill the sheet."
                            : "Finish steps 1 and 2 below to connect a Google Sheet."}
                    </p>
                )}

                {settings.last_sync_ok === false && settings.last_error && (
                    <div
                        role="alert"
                        className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm"
                    >
                        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
                        <p>{settings.last_error}</p>
                    </div>
                )}

                <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
                    The sheet is a <strong className="font-medium text-foreground">read-only copy</strong> of your leads. Anything typed into it is
                    overwritten at the next update, so share it with your team as <strong className="font-medium text-foreground">view only</strong> and
                    let them record status and notes in Market Scout. People on the do-not-contact list are never included.
                </p>
            </CardContent>
        </Card>
    );
};

export default SyncStatusCard;
