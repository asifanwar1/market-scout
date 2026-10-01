import { CheckCircle2, FileSpreadsheet, Loader2, XCircle } from "lucide-react";
import { useState } from "react";

import type { TSheetsSettings } from "@/api/services/sheets/sheets.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useTestSheets, useUpdateSheetsSettings } from "@/hooks/api/sheets.queries";
import { showToast } from "@/lib/toast";

type TSpreadsheetCardProps = {
    settings: TSheetsSettings;
};

const SpreadsheetCard = ({ settings }: TSpreadsheetCardProps) => {
    const { mutateAsync: update, isPending: isSaving } = useUpdateSheetsSettings();
    const { mutateAsync: test, isPending: isTesting, data: testResult, reset: resetTest } = useTestSheets();

    // undefined = untouched, so the box follows the saved link until the person types.
    const [typed, setTyped] = useState<string | undefined>(undefined);
    const [showDisconnect, setShowDisconnect] = useState(false);

    const link = typed ?? settings.spreadsheet_url ?? "";
    const isChanged = link.trim() !== (settings.spreadsheet_url ?? "");

    const handleSave = async () => {
        await update({ spreadsheet: link.trim() });
        setTyped(undefined);
        resetTest();
        showToast.success("Sheet saved");
    };

    const handleDisconnect = async () => {
        await update({ spreadsheet: "" });
        setTyped(undefined);
        setShowDisconnect(false);
        resetTest();
        showToast.success("Sheet disconnected");
    };

    const handleAutoSync = async (enabled: boolean) => {
        await update({ auto_sync: enabled });
        showToast.success(enabled ? "The sheet will update by itself" : "Automatic updates switched off");
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <FileSpreadsheet className="size-4" />
                    Step 2 · The Google Sheet
                </CardTitle>
                <CardDescription>
                    Paste the address of the sheet from your browser. Only a worksheet called "{settings.worksheet_title}" is used, and it is created if it isn't there.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
                <div className="space-y-2">
                    <Label htmlFor="spreadsheet-link">Sheet link</Label>
                    <div className="flex flex-wrap items-center gap-2">
                        <Input
                            id="spreadsheet-link"
                            placeholder="https://docs.google.com/spreadsheets/d/…"
                            autoComplete="off"
                            value={link}
                            onChange={(event) => setTyped(event.target.value)}
                            className="w-full sm:w-[28rem]"
                        />
                        <Button onClick={handleSave} disabled={!link.trim() || !isChanged || isSaving}>
                            Save
                        </Button>
                        {settings.spreadsheet_id && (
                            <Button variant="ghost" onClick={() => setShowDisconnect(true)} disabled={isSaving}>
                                Disconnect
                            </Button>
                        )}
                    </div>
                    {settings.spreadsheet_title && !isChanged && (
                        <p className="text-sm text-muted-foreground">
                            Spreadsheet: <span className="font-medium text-foreground">{settings.spreadsheet_title}</span>
                        </p>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <Button variant="outline" disabled={!settings.is_configured || isChanged || isTesting} onClick={() => test()}>
                        {isTesting && <Loader2 className="animate-spin" />}
                        Test connection
                    </Button>
                    {testResult && (
                        <p
                            role="status"
                            className={`flex items-start gap-1.5 text-sm ${testResult.ok ? "text-success-foreground" : "text-destructive"}`}
                        >
                            {testResult.ok ? (
                                <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                            ) : (
                                <XCircle className="mt-0.5 size-4 shrink-0" />
                            )}
                            {testResult.message}
                        </p>
                    )}
                </div>

                <div className="flex items-start justify-between gap-4 border-t pt-5">
                    <div className="space-y-1">
                        <Label htmlFor="auto-sync">Update the sheet automatically</Label>
                        <p className="text-sm text-muted-foreground">
                            Shortly after a run finishes, a lead is changed, or someone is put on the do-not-contact list. Turn it off to update only when you press Sync now.
                        </p>
                    </div>
                    <Switch id="auto-sync" checked={settings.auto_sync} disabled={isSaving} onCheckedChange={handleAutoSync} />
                </div>
            </CardContent>

            <ConfirmationModal
                open={showDisconnect}
                destructive
                title="Disconnect this sheet?"
                description="Market Scout stops updating it. The sheet and what it holds are left as they are."
                confirmText="Disconnect"
                isLoading={isSaving}
                onConfirm={handleDisconnect}
                onClose={() => setShowDisconnect(false)}
            />
        </Card>
    );
};

export default SpreadsheetCard;
