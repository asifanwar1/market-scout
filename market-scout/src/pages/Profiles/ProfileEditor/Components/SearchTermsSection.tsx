import { ChevronRight, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Controller, useFieldArray, useFormContext, useWatch } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { OSM_FILTER_EXAMPLE } from "@/utils/osmFilter.utils";
import type { TProfileFormValues } from "../profileForm";

type TTermRowProps = {
    index: number;
    onRemove: () => void;
};

const TermRow = ({ index, onRemove }: TTermRowProps) => {
    "use no memo";

    const {
        register,
        control,
        formState: { errors },
    } = useFormContext<TProfileFormValues>();
    const termErrors = errors.terms?.[index];
    const segments = useWatch({ control, name: "segments" });
    const osm = useWatch({ control, name: `terms.${index}.osm` }) ?? "";

    const [manuallyOpen, setManuallyOpen] = useState(false);
    const showOsm = manuallyOpen || osm.trim().length > 0 || !!termErrors?.osm;

    const renderSegment = (segment: (typeof segments)[number]) => (
        <SelectItem key={segment.key} value={segment.key}>
            {segment.name.trim() || "Untitled segment"}
        </SelectItem>
    );

    return (
        <li className="space-y-3 rounded-lg border p-3" data-testid={`term-${index}`}>
            <div className="grid gap-3 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_9rem_auto_auto] md:items-start">
                <div className="space-y-1.5">
                    <Label htmlFor={`term-text-${index}`} className="sr-only">
                        Search text
                    </Label>
                    <Input
                        id={`term-text-${index}`}
                        placeholder="What to search for, e.g. solar panel dealer"
                        aria-invalid={!!termErrors?.text}
                        {...register(`terms.${index}.text`)}
                    />
                    {termErrors?.text && <p className="text-sm text-destructive">{termErrors.text.message}</p>}
                </div>

                <div className="space-y-1.5">
                    <Controller
                        control={control}
                        name={`terms.${index}.segmentKey`}
                        render={({ field }) => (
                            <Select value={field.value} onValueChange={field.onChange}>
                                <SelectTrigger className="w-full" aria-label="Segment" aria-invalid={!!termErrors?.segmentKey}>
                                    <SelectValue placeholder="Segment" />
                                </SelectTrigger>
                                <SelectContent>{segments.map(renderSegment)}</SelectContent>
                            </Select>
                        )}
                    />
                    {termErrors?.segmentKey && (
                        <p className="text-sm text-destructive">{termErrors.segmentKey.message}</p>
                    )}
                </div>

                <Controller
                    control={control}
                    name={`terms.${index}.language`}
                    render={({ field }) => (
                        <Select value={field.value} onValueChange={field.onChange}>
                            <SelectTrigger className="w-full" aria-label="Language">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="en">English</SelectItem>
                                <SelectItem value="ur-roman">Roman Urdu</SelectItem>
                            </SelectContent>
                        </Select>
                    )}
                />

                <div className="flex h-9 items-center gap-2">
                    <Controller
                        control={control}
                        name={`terms.${index}.isActive`}
                        render={({ field }) => (
                            <Switch
                                checked={field.value}
                                onCheckedChange={field.onChange}
                                aria-label="Use this search in runs"
                            />
                        )}
                    />
                </div>

                <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Remove search term ${index + 1}`}
                    onClick={onRemove}
                >
                    <Trash2 />
                </Button>
            </div>

            <div>
                <button
                    type="button"
                    onClick={() => setManuallyOpen((open) => !open)}
                    className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                    aria-expanded={showOsm}
                >
                    <ChevronRight className={`size-3.5 transition-transform ${showOsm ? "rotate-90" : ""}`} />
                    OpenStreetMap filter
                    <span className="font-normal">
                        {osm.trim() ? "(set)" : "(not set: OpenStreetMap skips this search)"}
                    </span>
                </button>
                {showOsm && (
                    <div className="mt-2 space-y-1.5">
                        <Textarea
                            rows={3}
                            spellCheck={false}
                            className="font-mono text-xs"
                            aria-label="OpenStreetMap filter"
                            placeholder={OSM_FILTER_EXAMPLE}
                            aria-invalid={!!termErrors?.osm}
                            {...register(`terms.${index}.osm`)}
                        />
                        {termErrors?.osm ? (
                            <p className="text-sm text-destructive">{termErrors.osm.message}</p>
                        ) : (
                            <p className="text-xs text-muted-foreground">
                                One alternative per line; join conditions on a line with AND. <span className="font-mono">key=value</span>{" "}
                                is an exact match, <span className="font-mono">key~pattern</span> is a case-insensitive pattern.
                                Example: <span className="font-mono">{OSM_FILTER_EXAMPLE}</span>
                            </p>
                        )}
                    </div>
                )}
            </div>
        </li>
    );
};

const SearchTermsSection = () => {
    "use no memo";

    const {
        control,
        formState: { errors },
    } = useFormContext<TProfileFormValues>();
    const { fields, append, remove } = useFieldArray({ control, name: "terms" });
    const segments = useWatch({ control, name: "segments" });

    const renderField = (field: (typeof fields)[number], index: number) => (
        <TermRow key={field.id} index={index} onRemove={() => remove(index)} />
    );
    return (
        <Card>
            <CardHeader>
                <CardTitle>Search terms</CardTitle>
                <CardDescription>
                    What each source is asked. Hosted sources (Google Places, HERE, TomTom) use the text as written; OpenStreetMap,
                    Overture Maps and Foursquare need a filter (tags and name patterns) because they don't do free-text search.
                </CardDescription>
                <CardAction>
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={segments.length === 0}
                        onClick={() =>
                            append({
                                text: "",
                                segmentKey: segments[0]?.key ?? "",
                                language: "en",
                                isActive: true,
                                osm: "",
                            })
                        }
                    >
                        <Plus />
                        Add search term
                    </Button>
                </CardAction>
            </CardHeader>
            <CardContent>
                {segments.length === 0 && (
                    <p className="text-sm text-muted-foreground">Add a segment first; every search term belongs to one.</p>
                )}
                {segments.length > 0 && fields.length === 0 && (
                    <p className="text-sm text-muted-foreground">No search terms yet.</p>
                )}
                <ul className="space-y-3">
                    {fields.map(renderField)}
                </ul>
                {typeof errors.terms?.message === "string" && (
                    <p className="mt-2 text-sm text-destructive">{errors.terms.message}</p>
                )}
            </CardContent>
        </Card>
    );
};

export default SearchTermsSection;
