import { Loader2 } from "lucide-react";
import { useState, type ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { QUALITY_SETTING_LIMITS } from "@/constants/quality.constants";
import { useGetQualitySettings, useUpdateQualitySettings } from "@/hooks/api/quality.queries";
import { showToast } from "@/lib/toast";
import { parseWholeNumber } from "@/utils/alert.utils";
import { AFTER_RUNS_LABEL, PER_RUN_LABEL, SETTINGS_DESCRIPTION, SETTINGS_TITLE } from "../Quality.constants";

type TDraft = {
    checkAfterRuns: boolean;
    maxPerRun: string;
};

const QualitySettingsCard = () => {
    const { data: settings } = useGetQualitySettings();
    const { mutateAsync: update, isPending } = useUpdateQualitySettings();
    const [draft, setDraft] = useState<TDraft | null>(null);

    if (!settings) return null;

    const form = draft ?? { checkAfterRuns: settings.check_after_runs, maxPerRun: String(settings.max_checks_per_run) };
    const maxPerRun = parseWholeNumber(form.maxPerRun, QUALITY_SETTING_LIMITS.PER_RUN);
    const canSave = draft !== null && maxPerRun !== null && !isPending;

    const changeSwitch = (checked: boolean) => {
        setDraft({ ...form, checkAfterRuns: checked });
    };

    const changeNumber = (event: ChangeEvent<HTMLInputElement>) => {
        setDraft({ ...form, maxPerRun: event.target.value });
    };

    const save = async () => {
        if (maxPerRun === null) return;
        await update({ check_after_runs: form.checkAfterRuns, max_checks_per_run: maxPerRun });
        setDraft(null);
        showToast.success("Settings saved");
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>{SETTINGS_TITLE}</CardTitle>
                <CardDescription>{SETTINGS_DESCRIPTION}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
                <div className="flex items-start justify-between gap-4">
                    <Label htmlFor="quality-after-runs">{AFTER_RUNS_LABEL}</Label>
                    <Switch id="quality-after-runs" checked={form.checkAfterRuns} onCheckedChange={changeSwitch} />
                </div>
                <div className="space-y-1.5">
                    <Label htmlFor="quality-per-run">{PER_RUN_LABEL}</Label>
                    <Input
                        id="quality-per-run"
                        inputMode="numeric"
                        disabled={!form.checkAfterRuns}
                        value={form.maxPerRun}
                        onChange={changeNumber}
                        className="w-full sm:w-40"
                    />
                </div>
                <Button disabled={!canSave} onClick={save}>
                    {isPending && <Loader2 className="animate-spin" />}
                    Save settings
                </Button>
            </CardContent>
        </Card>
    );
};

export default QualitySettingsCard;
