import { CheckCircle2, Database, KeyRound, Loader2, XCircle } from "lucide-react";
import { useState } from "react";

import type { TSource } from "@/api/services/sources/sources.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import StatusBadge from "@/components/custom/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useTestSource, useUpdateSource } from "@/hooks/api/sources.queries";
import { showToast } from "@/lib/toast";

const MIN_KEY_LENGTH = 8;

type TSourceCardProps = {
    source: TSource;
};

const availability = (source: TSource) => {
    if (source.is_available) return { label: "In use", className: "bg-success text-success-foreground" };
    if (source.requires_api_key && !source.has_key) {
        return { label: "Needs a key", className: "bg-warning text-warning-foreground" };
    }
    if (source.is_enabled && source.requires_dataset && !source.dataset_ready) {
        return { label: "Needs a download", className: "bg-warning text-warning-foreground" };
    }
    return { label: "Switched off", className: "bg-muted text-muted-foreground" };
};

const SourceCard = ({ source }: TSourceCardProps) => {
    const { mutateAsync: updateSource, isPending: isSaving } = useUpdateSource();
    const { mutateAsync: testSource, isPending: isTesting, data: testResult, reset: resetTest } = useTestSource();

    const [apiKey, setApiKey] = useState("");
    const [showRemove, setShowRemove] = useState(false);

    const status = availability(source);
    const canToggle = !source.requires_api_key || source.has_key;
    const inputId = `key-${source.key}`;

    const handleToggle = async (enabled: boolean) => {
        await updateSource({ key: source.key, body: { is_enabled: enabled } });
        showToast.success(`${source.name} ${enabled ? "switched on" : "switched off"}`);
        resetTest();
    };

    const handleSaveKey = async () => {
        await updateSource({
            key: source.key,
            body: { api_key: apiKey.trim(), ...(source.is_enabled ? {} : { is_enabled: true }) },
        });
        setApiKey("");
        resetTest();
        showToast.success(`Key saved${source.is_enabled ? "" : `, ${source.name} switched on`}`);
    };

    const handleRemoveKey = async () => {
        await updateSource({ key: source.key, body: { clear_api_key: true } });
        setShowRemove(false);
        resetTest();
        showToast.success("Saved key removed");
    };

    return (
        <Card>
            <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1.5">
                        <CardTitle className="flex flex-wrap items-center gap-2">
                            {source.name}
                            {source.is_paid ? (
                                <Badge variant="secondary" className="bg-warning font-normal text-warning-foreground">
                                    Paid
                                </Badge>
                            ) : (
                                <Badge variant="outline" className="font-normal">
                                    Free
                                </Badge>
                            )}
                        </CardTitle>
                        <CardDescription>{source.description}</CardDescription>
                    </div>
                    <div className="flex items-center gap-3">
                        <StatusBadge label={status.label} className={status.className} />
                        <div className="flex items-center gap-2">
                            <Label htmlFor={`enable-${source.key}`} className="text-sm font-normal">
                                Enabled
                            </Label>
                            <Switch
                                id={`enable-${source.key}`}
                                checked={source.is_enabled}
                                disabled={!canToggle || isSaving}
                                onCheckedChange={handleToggle}
                            />
                        </div>
                    </div>
                </div>
            </CardHeader>

            {(source.requires_api_key || source.requires_dataset || source.kind === "discovery") && (
                <CardContent className="space-y-5 border-t pt-5">
                    {source.requires_dataset && (
                        <div className="flex items-start gap-3 text-sm">
                            <Database className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                            <div className="space-y-1">
                                <p className="font-medium">Data on this computer</p>
                                <p className={source.dataset_ready ? "text-muted-foreground" : "text-warning-foreground"}>{source.dataset_note}</p>
                                {source.dataset_ready && (
                                    <p className="text-xs text-muted-foreground">
                                        To refresh it, run <span className="font-mono">python -m scripts.download_overture</span> in the backend folder.
                                    </p>
                                )}
                            </div>
                        </div>
                    )}

                    {source.requires_api_key && (
                        <div className="space-y-3">
                            <div>
                                <Label htmlFor={inputId} className="flex items-center gap-1.5">
                                    <KeyRound className="size-4" />
                                    API key
                                </Label>
                                <p className="mt-1 text-sm text-muted-foreground">
                                    {source.has_key && source.key_source === "saved" && (
                                        <>
                                            A key ending <span className="font-mono">{source.key_hint}</span> is saved. It is stored encrypted and can't be shown again.
                                        </>
                                    )}
                                    {source.has_key && source.key_source === "environment" && (
                                        <>
                                            Using the key set on the server (<span className="font-mono">{source.key_hint}</span>). Save one here to override it.
                                        </>
                                    )}
                                    {!source.has_key && !source.key_needs_reentry && "No key yet. Paste one below to switch this source on."}
                                    {source.key_needs_reentry && (
                                        <span className="text-destructive">
                                            The saved key can no longer be read (the server's secret changed). Enter it again.
                                        </span>
                                    )}
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                <Input
                                    id={inputId}
                                    type="password"
                                    autoComplete="off"
                                    placeholder={source.has_key ? "Paste a new key to replace it" : "Paste your API key"}
                                    value={apiKey}
                                    onChange={(event) => setApiKey(event.target.value)}
                                    className="w-full sm:w-80"
                                />
                                <Button
                                    onClick={handleSaveKey}
                                    disabled={apiKey.trim().length < MIN_KEY_LENGTH || isSaving}
                                >
                                    Save key
                                </Button>
                                {source.key_source === "saved" && (
                                    <Button variant="ghost" onClick={() => setShowRemove(true)} disabled={isSaving}>
                                        Remove saved key
                                    </Button>
                                )}
                            </div>
                            {source.is_paid && (
                                <p className="text-xs text-muted-foreground">
                                    Billed per request by the provider. Every run shows an estimate first and can carry a spending cap.
                                </p>
                            )}
                        </div>
                    )}

                    {source.kind === "discovery" && (
                        <div className="flex flex-wrap items-center gap-3">
                            <Button
                                variant="outline"
                                disabled={isTesting || (source.requires_api_key && !source.has_key)}
                                onClick={() => testSource(source.key)}
                            >
                                {isTesting && <Loader2 className="animate-spin" />}
                                Test connection
                            </Button>
                            {testResult && (
                                <p
                                    role="status"
                                    className={`flex items-center gap-1.5 text-sm ${
                                        testResult.ok ? "text-success-foreground" : "text-destructive"
                                    }`}
                                >
                                    {testResult.ok ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
                                    {testResult.message}
                                </p>
                            )}
                        </div>
                    )}
                </CardContent>
            )}

            <ConfirmationModal
                open={showRemove}
                destructive
                title="Remove the saved key?"
                description={`${source.name} will be switched off unless a key is also set on the server.`}
                confirmText="Remove key"
                isLoading={isSaving}
                onConfirm={handleRemoveKey}
                onClose={() => setShowRemove(false)}
            />
        </Card>
    );
};

export default SourceCard;
