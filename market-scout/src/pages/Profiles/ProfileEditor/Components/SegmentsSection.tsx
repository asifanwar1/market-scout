import { Plus, Trash2 } from "lucide-react";
import { useFieldArray, useFormContext } from "react-hook-form";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { newKey, type TProfileFormValues } from "../profileForm";

const SegmentsSection = () => {
    "use no memo";

    const {
        register,
        control,
        getValues,
        setValue,
        formState: { errors },
    } = useFormContext<TProfileFormValues>();
    const { fields, append, remove } = useFieldArray({ control, name: "segments" });

    const removeSegment = (index: number) => {
        const key = getValues(`segments.${index}.key`);
        setValue(
            "terms",
            getValues("terms").filter((term) => term.segmentKey !== key),
            { shouldDirty: true },
        );
        remove(index);
    };

    const renderField = (field: (typeof fields)[number], index: number) => {
        const segmentErrors = errors.segments?.[index];
        return (
            <div key={field.id} className="space-y-3 rounded-lg border p-4" data-testid={`segment-${index}`}>
                <div className="flex items-start gap-3">
                    <div className="grid flex-1 gap-3 sm:grid-cols-2">
                        <div className="space-y-1.5">
                            <Label htmlFor={`segment-name-${index}`}>Name</Label>
                            <Input
                                id={`segment-name-${index}`}
                                aria-invalid={!!segmentErrors?.name}
                                {...register(`segments.${index}.name`)}
                            />
                            {segmentErrors?.name && (
                                <p className="text-sm text-destructive">{segmentErrors.name.message}</p>
                            )}
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor={`segment-description-${index}`}>Description</Label>
                            <Input
                                id={`segment-description-${index}`}
                                {...register(`segments.${index}.description`)}
                            />
                        </div>
                    </div>
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        className="mt-6"
                        aria-label={`Remove segment ${index + 1}`}
                        onClick={() => removeSegment(index)}
                    >
                        <Trash2 />
                    </Button>
                </div>

                <div className="space-y-1.5">
                    <Label htmlFor={`segment-patterns-${index}`}>
                        Name patterns <span className="font-normal text-muted-foreground">(optional, one per line)</span>
                    </Label>
                    <Textarea
                        id={`segment-patterns-${index}`}
                        rows={3}
                        spellCheck={false}
                        className="font-mono text-xs"
                        placeholder={"\\bdealer\nauthori[sz]ed"}
                        aria-invalid={!!segmentErrors?.patterns}
                        {...register(`segments.${index}.patterns`)}
                    />
                    {segmentErrors?.patterns ? (
                        <p className="text-sm text-destructive">{segmentErrors.patterns.message}</p>
                    ) : (
                        <p className="text-xs text-muted-foreground">
                            If a business's name matches one of these, it belongs here whichever search found it.
                        </p>
                    )}
                </div>

                {getValues(`segments.${index}.slug`) && (
                    <p className="text-xs text-muted-foreground">
                        Identifier <Badge variant="outline" className="ml-1 font-mono">{getValues(`segments.${index}.slug`)}</Badge>{" "}
                        (stays the same if you rename it)
                    </p>
                )}
            </div>
        );
    };
    return (
        <Card>
            <CardHeader>
                <CardTitle>Segments</CardTitle>
                <CardDescription>
                    The kinds of business you sort leads into (dealer, importer, installer…). A business is placed in a segment
                    by which search found it, and its name can move it to a better fit.
                </CardDescription>
                <CardAction>
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => append({ key: newKey(), slug: "", name: "", description: "", patterns: "" })}
                    >
                        <Plus />
                        Add segment
                    </Button>
                </CardAction>
            </CardHeader>
            <CardContent className="space-y-4">
                {fields.length === 0 && (
                    <p className="text-sm text-muted-foreground">No segments yet. Add at least one, then give it search terms.</p>
                )}

                {fields.map(renderField)}
                {typeof errors.segments?.message === "string" && (
                    <p className="text-sm text-destructive">{errors.segments.message}</p>
                )}
            </CardContent>
        </Card>
    );
};

export default SegmentsSection;
