import { Loader2, Undo2, Wand2 } from "lucide-react";
import { useState } from "react";

import type { TScoringTrait } from "@/api/services/quality/quality.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useGetProfiles } from "@/hooks/api/catalog.queries";
import { useApplyScoring, useGetScoring, useRevertScoring } from "@/hooks/api/quality.queries";
import { showToast } from "@/lib/toast";
import { formatRate, describeTrait, weightChange } from "@/utils/quality.utils";
import { APPLY_DESCRIPTION, APPLY_TITLE, SCORING_DESCRIPTION, SCORING_NEEDS_MORE, SCORING_TITLE } from "../Quality.constants";

const ScoringCard = () => {
    const { data: profilesData } = useGetProfiles();
    const profiles = profilesData?.data ?? [];
    const [chosenId, setChosenId] = useState<number | null>(null);
    const [isApplyOpen, setIsApplyOpen] = useState(false);
    const profileId = chosenId ?? profiles[0]?.id;

    const { data: report, isPending } = useGetScoring(profileId);
    const { mutateAsync: apply, isPending: isApplying } = useApplyScoring();
    const { mutateAsync: revert, isPending: isReverting } = useRevertScoring();

    const onProfileChange = (value: string) => {
        setChosenId(Number(value));
    };

    const confirmApply = async () => {
        if (profileId === undefined) return;
        const result = await apply({ profile_id: profileId });
        setIsApplyOpen(false);
        showToast.success(`Weights updated and ${result.rescored} leads rescored`);
    };

    const undo = async () => {
        if (profileId === undefined) return;
        const result = await revert({ profile_id: profileId });
        showToast.success(`Earlier weights restored and ${result.rescored} leads rescored`);
    };

    const renderProfile = (profile: { id: number; name: string }) => (
        <SelectItem key={profile.id} value={String(profile.id)}>
            {profile.name}
        </SelectItem>
    );

    const renderTrait = (trait: TScoringTrait) => {
        const change = weightChange(trait);
        return (
            <TableRow key={trait.key}>
                <TableCell className="min-w-48">
                    <p className="font-medium">{trait.label}</p>
                    <p className="text-xs text-muted-foreground">{describeTrait(trait)}</p>
                </TableCell>
                <TableCell className="tabular-nums">
                    {formatRate(trait.win_rate_with)} <span className="text-xs text-muted-foreground">of {trait.with_count}</span>
                </TableCell>
                <TableCell className="tabular-nums">
                    {formatRate(trait.win_rate_without)} <span className="text-xs text-muted-foreground">of {trait.without_count}</span>
                </TableCell>
                <TableCell className="tabular-nums">
                    {trait.current_weight}
                    {change !== 0 && (
                        <>
                            {" → "}
                            <span className="font-medium">{trait.suggested_weight}</span>
                        </>
                    )}
                </TableCell>
                <TableCell className="min-w-40 text-xs text-muted-foreground">
                    {trait.significant && <Badge variant="secondary" className="mr-1">Clear</Badge>}
                    {trait.note}
                </TableCell>
            </TableRow>
        );
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>{SCORING_TITLE}</CardTitle>
                <CardDescription>{SCORING_DESCRIPTION}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {profiles.length > 1 && (
                    <div className="space-y-1.5">
                        <Label htmlFor="scoring-profile">Profile</Label>
                        <Select value={profileId === undefined ? undefined : String(profileId)} onValueChange={onProfileChange}>
                            <SelectTrigger id="scoring-profile" className="w-full sm:w-72">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>{profiles.map(renderProfile)}</SelectContent>
                        </Select>
                    </div>
                )}

                {isPending || !report ? (
                    <Loading />
                ) : (
                    <>
                        <p className="text-sm">
                            <span className="font-medium">{report.closed}</span> closed deals: {report.won} won, {report.lost} lost.
                        </p>
                        {!report.enough_data && (
                            <p className="text-sm text-muted-foreground">
                                {SCORING_NEEDS_MORE.replace("{needed}", String(report.needed)).replace("{closed}", String(report.closed))}
                            </p>
                        )}
                        {report.closed > 0 && (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Trait</TableHead>
                                        <TableHead>Won, with it</TableHead>
                                        <TableHead>Won, without it</TableHead>
                                        <TableHead>Weight</TableHead>
                                        <TableHead>Reading</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>{report.traits.map(renderTrait)}</TableBody>
                            </Table>
                        )}
                        <div className="flex flex-wrap gap-2">
                            <Button disabled={!report.can_apply || isApplying} onClick={() => setIsApplyOpen(true)}>
                                <Wand2 />
                                Apply suggested weights
                            </Button>
                            <Button variant="outline" disabled={!report.can_revert || isReverting} onClick={undo}>
                                {isReverting ? <Loader2 className="animate-spin" /> : <Undo2 />}
                                Undo last change
                            </Button>
                        </div>
                    </>
                )}
            </CardContent>

            <ConfirmationModal
                open={isApplyOpen}
                title={APPLY_TITLE}
                description={APPLY_DESCRIPTION}
                confirmText="Apply"
                isLoading={isApplying}
                onConfirm={confirmApply}
                onClose={() => setIsApplyOpen(false)}
            />
        </Card>
    );
};

export default ScoringCard;
