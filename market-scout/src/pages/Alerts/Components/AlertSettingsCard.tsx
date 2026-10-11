import { Loader2 } from "lucide-react";
import { useState, type ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useGetAlertSettings, useUpdateAlertSettings } from "@/hooks/api/alerts.queries";
import { showToast } from "@/lib/toast";
import { toSettingsBody, toSettingsForm, type TAlertSettingsForm } from "@/utils/alert.utils";
import { SETTINGS_DESCRIPTION, SETTINGS_TITLE } from "../Alerts.constants";

type TNumberField = "newLeadMinScore" | "growingMinNewReviews" | "growingMinPercent" | "maxPerRun";
type TSwitchField = "newLeadEnabled" | "growingEnabled" | "reachableEnabled";

const AlertSettingsCard = () => {
    const { data: settings } = useGetAlertSettings(true);
    const { mutateAsync: update, isPending } = useUpdateAlertSettings();
    const [draft, setDraft] = useState<TAlertSettingsForm | null>(null);

    if (!settings) return null;

    const form = draft ?? toSettingsForm(settings);
    const body = toSettingsBody(form);
    const canSave = draft !== null && body !== null && !isPending;

    const changeSwitch = (field: TSwitchField, checked: boolean) => {
        setDraft({ ...form, [field]: checked });
    };

    const changeNumber = (field: TNumberField, event: ChangeEvent<HTMLInputElement>) => {
        setDraft({ ...form, [field]: event.target.value });
    };

    const save = async () => {
        if (!body) return;
        await update(body);
        setDraft(null);
        showToast.success("Alert settings saved");
    };

    const renderSwitch = (field: TSwitchField, label: string, hint: string) => (
        <div className="flex items-start justify-between gap-4">
            <div>
                <Label htmlFor={`alert-${field}`}>{label}</Label>
                <p className="text-xs text-muted-foreground">{hint}</p>
            </div>
            <Switch id={`alert-${field}`} checked={form[field]} onCheckedChange={(checked) => changeSwitch(field, checked)} />
        </div>
    );

    const renderNumber = (field: TNumberField, label: string, isDisabled: boolean) => (
        <div className="space-y-1.5">
            <Label htmlFor={`alert-${field}`}>{label}</Label>
            <Input
                id={`alert-${field}`}
                inputMode="numeric"
                disabled={isDisabled}
                value={form[field]}
                onChange={(event) => changeNumber(field, event)}
                className="w-full sm:w-40"
            />
        </div>
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>{SETTINGS_TITLE}</CardTitle>
                <CardDescription>{SETTINGS_DESCRIPTION}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="space-y-3">
                    {renderSwitch("newLeadEnabled", "New leads", "A search finds a business that is not in Leads yet and it scores at least this much.")}
                    {renderNumber("newLeadMinScore", "Lowest score (0-100)", !form.newLeadEnabled)}
                </div>
                <div className="space-y-3 border-t pt-5">
                    {renderSwitch("growingEnabled", "Growing businesses", "A business's review count rose a lot since the last time it was seen. Only sources that report reviews can show this.")}
                    <div className="flex flex-wrap gap-4">
                        {renderNumber("growingMinNewReviews", "At least this many new reviews", !form.growingEnabled)}
                        {renderNumber("growingMinPercent", "and at least this much growth (%)", !form.growingEnabled)}
                    </div>
                </div>
                <div className="space-y-3 border-t pt-5">
                    {renderSwitch("reachableEnabled", "Newly reachable", "A lead that had no phone, email or WhatsApp now has one.")}
                </div>
                <div className="space-y-3 border-t pt-5">
                    {renderNumber("maxPerRun", "Most alerts from one run (best first)", false)}
                </div>
                <Button disabled={!canSave} onClick={save}>
                    {isPending && <Loader2 className="animate-spin" />}
                    Save settings
                </Button>
            </CardContent>
        </Card>
    );
};

export default AlertSettingsCard;
