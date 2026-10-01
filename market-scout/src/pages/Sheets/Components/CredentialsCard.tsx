import { KeyRound } from "lucide-react";
import { useState } from "react";

import type { TSheetsSettings } from "@/api/services/sheets/sheets.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import CopyButton from "@/components/custom/CopyButton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useUpdateSheetsSettings } from "@/hooks/api/sheets.queries";
import { showToast } from "@/lib/toast";
import { CREDENTIALS_SOURCE } from "@/constants/source.constants";

type TCredentialsCardProps = {
    settings: TSheetsSettings;
};

const CredentialsCard = ({ settings }: TCredentialsCardProps) => {
    const { mutateAsync: update, isPending } = useUpdateSheetsSettings();
    const [json, setJson] = useState("");
    const [showRemove, setShowRemove] = useState(false);

    const handleSave = async () => {
        await update({ credentials_json: json.trim() });
        setJson("");
        showToast.success("Key saved");
    };

    const handleRemove = async () => {
        await update({ clear_credentials: true });
        setShowRemove(false);
        showToast.success("Saved key removed");
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <KeyRound className="size-4" />
                    Step 1 · Google key
                </CardTitle>
                <CardDescription>The downloaded key file that lets Market Scout write to your sheet.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {settings.has_credentials && settings.service_account_email && (
                    <div className="space-y-1 rounded-md border bg-muted/40 p-3">
                        <p className="text-sm">
                            {settings.credentials_source === CREDENTIALS_SOURCE.ENVIRONMENT
                                ? "Using the key set on the server."
                                : "A key is saved. It is stored encrypted and can't be shown again."}{" "}
                            Share your Google Sheet with this address, as an <span className="font-medium">Editor</span>:
                        </p>
                        <p className="flex items-center gap-1 font-mono text-sm break-all">
                            {settings.service_account_email}
                            <CopyButton value={settings.service_account_email} label="the address" />
                        </p>
                    </div>
                )}

                {settings.credentials_needs_reentry && (
                    <p className="text-sm text-destructive">
                        The saved key can no longer be read (the server's secret changed). Paste it again.
                    </p>
                )}

                <div className="space-y-2">
                    <Label htmlFor="credentials-json">
                        {settings.has_credentials ? "Replace the key" : "Paste the key file's contents"}
                    </Label>
                    <Textarea
                        id="credentials-json"
                        rows={4}
                        spellCheck={false}
                        autoComplete="off"
                        placeholder={'{ "type": "service_account", … }'}
                        value={json}
                        onChange={(event) => setJson(event.target.value)}
                        className="max-h-56 font-mono text-xs"
                    />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <Button onClick={handleSave} disabled={!json.trim() || isPending}>
                        Save key
                    </Button>
                    {settings.credentials_source === CREDENTIALS_SOURCE.SAVED && (
                        <Button variant="ghost" onClick={() => setShowRemove(true)} disabled={isPending}>
                            Remove saved key
                        </Button>
                    )}
                </div>
            </CardContent>

            <ConfirmationModal
                open={showRemove}
                destructive
                title="Remove the saved key?"
                description="The sheet will stop updating until a key is added again. The sheet itself is left as it is."
                confirmText="Remove key"
                isLoading={isPending}
                onConfirm={handleRemove}
                onClose={() => setShowRemove(false)}
            />
        </Card>
    );
};

export default CredentialsCard;
