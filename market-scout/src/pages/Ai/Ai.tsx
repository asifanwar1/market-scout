import { CheckCircle2, KeyRound, Loader2, XCircle } from "lucide-react";

import type { TAiModel } from "@/api/services/ai/ai.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { formatAiCost } from "@/utils/ai.utils";
import {
    AI_PAGE_DESCRIPTION,
    AI_PAGE_TITLE,
    BUDGET_HELP,
    HOW_IT_WORKS,
    KEY_HELP,
    KEY_PLACEHOLDER,
    MODEL_HELP,
    REMOVE_KEY_DESCRIPTION,
    REMOVE_KEY_TITLE,
} from "./Ai.constants";
import { useAiPage } from "./Ai.Container";

const Ai = () => {
    const {
        settings,
        isPending,
        isSaving,
        isTesting,
        testResult,
        models,
        selectedModel,
        apiKey,
        budgetValue,
        isBudgetValid,
        canSaveBudget,
        canSaveKey,
        canTest,
        canEnable,
        hasSavedKey,
        spentPercent,
        spentText,
        remainingText,
        isRemoveOpen,
        onApiKeyChange,
        onBudgetChange,
        saveKey,
        openRemove,
        closeRemove,
        confirmRemove,
        toggleEnabled,
        changeModel,
        saveBudget,
        testKey,
    } = useAiPage();

    const renderModel = (model: TAiModel) => (
        <SelectItem key={model.id} value={model.id}>
            {model.label} · {formatAiCost(model.input_per_mtok_usd)} in / {formatAiCost(model.output_per_mtok_usd)} out
        </SelectItem>
    );
    const renderNote = (note: string) => <li key={note}>{note}</li>;

    return (
        <div className="space-y-6">
            <PageHeader title={AI_PAGE_TITLE} description={AI_PAGE_DESCRIPTION} />

            {isPending || !settings ? (
                <Loading />
            ) : (
                <>
                    <Card>
                        <CardHeader>
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div className="space-y-1.5">
                                    <CardTitle>Connection</CardTitle>
                                    <CardDescription>{KEY_HELP}</CardDescription>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Label htmlFor="ai-enabled" className="text-sm font-normal">
                                        Enabled
                                    </Label>
                                    <Switch id="ai-enabled" checked={settings.is_enabled} disabled={!canEnable || isSaving} onCheckedChange={toggleEnabled} />
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4 border-t pt-5">
                            <div className="space-y-2">
                                <Label htmlFor="ai-key" className="flex items-center gap-1.5">
                                    <KeyRound className="size-4" />
                                    API key
                                </Label>
                                <p className="text-sm text-muted-foreground">
                                    {settings.has_key && settings.key_source === "saved" && (
                                        <>
                                            A key ending <span className="font-mono">{settings.key_hint}</span> is saved.
                                        </>
                                    )}
                                    {settings.has_key && settings.key_source === "environment" && (
                                        <>
                                            Using the key set on the server (<span className="font-mono">{settings.key_hint}</span>). Save one here to override it.
                                        </>
                                    )}
                                    {!settings.has_key && !settings.key_needs_reentry && "No key yet. Paste one below, then switch the assistant on."}
                                    {settings.key_needs_reentry && (
                                        <span className="text-destructive">The saved key can no longer be read (the server's secret changed). Enter it again.</span>
                                    )}
                                </p>
                                <div className="flex flex-wrap items-center gap-2">
                                    <Input
                                        id="ai-key"
                                        type="password"
                                        autoComplete="off"
                                        placeholder={KEY_PLACEHOLDER}
                                        value={apiKey}
                                        onChange={onApiKeyChange}
                                        className="w-full sm:w-96"
                                    />
                                    <Button disabled={!canSaveKey} onClick={saveKey}>
                                        Save key
                                    </Button>
                                    {hasSavedKey && (
                                        <Button variant="ghost" disabled={isSaving} onClick={openRemove}>
                                            Remove saved key
                                        </Button>
                                    )}
                                </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-3">
                                <Button variant="outline" disabled={!canTest} onClick={testKey}>
                                    {isTesting && <Loader2 className="animate-spin" />}
                                    Test connection
                                </Button>
                                {testResult && (
                                    <p
                                        role="status"
                                        className={`flex items-center gap-1.5 text-sm ${testResult.ok ? "text-success-foreground" : "text-destructive"}`}
                                    >
                                        {testResult.ok ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
                                        {testResult.message}
                                    </p>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Model and budget</CardTitle>
                            <CardDescription>{MODEL_HELP}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-5 border-t pt-5">
                            <div className="space-y-1.5">
                                <Label htmlFor="ai-model">Model</Label>
                                <Select value={settings.model} disabled={isSaving} onValueChange={changeModel}>
                                    <SelectTrigger id="ai-model" className="w-full sm:w-[28rem]">
                                        <SelectValue placeholder={selectedModel?.label} />
                                    </SelectTrigger>
                                    <SelectContent>{models.map(renderModel)}</SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-1.5">
                                <Label htmlFor="ai-budget">Monthly budget (USD)</Label>
                                <div className="flex flex-wrap items-center gap-2">
                                    <Input
                                        id="ai-budget"
                                        inputMode="decimal"
                                        value={budgetValue}
                                        aria-invalid={!isBudgetValid}
                                        onChange={onBudgetChange}
                                        className="w-40"
                                    />
                                    <Button disabled={!canSaveBudget} onClick={saveBudget}>
                                        Save budget
                                    </Button>
                                </div>
                                <p className="text-xs text-muted-foreground">{BUDGET_HELP}</p>
                            </div>

                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span>{spentText} spent this month</span>
                                    <span className="text-muted-foreground">{remainingText} left · {settings.analyses_this_month} analyses</span>
                                </div>
                                <Progress value={spentPercent} aria-label="Spent this month" />
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>How it works</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">{HOW_IT_WORKS.map(renderNote)}</ul>
                        </CardContent>
                    </Card>
                </>
            )}

            <ConfirmationModal
                open={isRemoveOpen}
                destructive
                title={REMOVE_KEY_TITLE}
                description={REMOVE_KEY_DESCRIPTION}
                confirmText="Remove key"
                isLoading={isSaving}
                onConfirm={confirmRemove}
                onClose={closeRemove}
            />
        </div>
    );
};

export default Ai;
