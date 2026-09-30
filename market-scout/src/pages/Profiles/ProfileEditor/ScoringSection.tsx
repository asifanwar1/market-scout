import { useFormContext, useWatch } from "react-hook-form";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SCORING_FIELDS, type TProfileFormValues } from "./profileForm";

const ScoringSection = () => {
    "use no memo"; // React Hook Form + React Compiler: see README

    const {
        register,
        control,
        formState: { errors },
    } = useFormContext<TProfileFormValues>();
    const scoring = useWatch({ control, name: "scoring" });
    const total = Object.values(scoring).reduce((sum, value) => sum + (Number.isFinite(value) ? value : 0), 0);

    return (
        <Card>
            <CardHeader>
                <CardTitle>Lead score</CardTitle>
                <CardDescription>
                    Points a lead earns for each thing we know about it. Leads are listed best first, so put the most weight on
                    what makes a lead easiest to act on. The score never goes above 100.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                    {SCORING_FIELDS.map((item) => (
                        <div key={item.name} className="space-y-1.5">
                            <Label htmlFor={`scoring-${item.name}`}>{item.label}</Label>
                            <Input
                                id={`scoring-${item.name}`}
                                type="number"
                                min={0}
                                max={100}
                                inputMode="numeric"
                                aria-invalid={!!errors.scoring?.[item.name]}
                                {...register(`scoring.${item.name}`, { valueAsNumber: true })}
                            />
                            {errors.scoring?.[item.name] ? (
                                <p className="text-sm text-destructive">{errors.scoring[item.name]?.message}</p>
                            ) : (
                                <p className="text-xs text-muted-foreground">{item.help}</p>
                            )}
                        </div>
                    ))}
                </div>
                <p className="text-sm text-muted-foreground">
                    A lead with everything scores <span className="font-medium text-foreground">{Math.min(100, total)}</span>
                    {total > 100 && " (capped at 100)"}.
                </p>
            </CardContent>
        </Card>
    );
};

export default ScoringSection;
