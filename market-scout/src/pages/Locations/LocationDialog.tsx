import { zodResolver } from "@hookform/resolvers/zod";
import { ExternalLink, Loader2 } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { TGeographyNode } from "@/api/services/geographies/geographies.response.types";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateGeography, useUpdateGeography } from "@/hooks/api/geographies.queries";
import { showToast } from "@/lib/toast";

const nameRule = z.string().trim().min(2, "At least 2 characters").max(100, "At most 100 characters");
const numberError = "Enter a number";

const provinceSchema = z.object({
    name: nameRule,
    latitude: z.number().optional(),
    longitude: z.number().optional(),
    radius_km: z.number().optional(),
});

const citySchema = z.object({
    name: nameRule,
    latitude: z.number({ error: numberError }).min(-90, "Between -90 and 90").max(90, "Between -90 and 90"),
    longitude: z.number({ error: numberError }).min(-180, "Between -180 and 180").max(180, "Between -180 and 180"),
    radius_km: z.number({ error: numberError }).gt(0, "More than 0").max(100, "At most 100 km"),
});

type TFormValues = {
    name: string;
    latitude?: number;
    longitude?: number;
    radius_km?: number;
};

export type TLocationDialogState =
    | { kind: "province"; node: null; parent: TGeographyNode }      // adding: parent is the country
    | { kind: "province"; node: TGeographyNode; parent: null }      // renaming
    | { kind: "city"; node: null; parent: TGeographyNode }          // adding: parent is the province
    | { kind: "city"; node: TGeographyNode; parent: null };         // editing

type TLocationDialogProps = {
    state: TLocationDialogState | null;
    onClose: () => void;
};

const LocationDialog = ({ state, onClose }: TLocationDialogProps) => {
    "use no memo"; // React Hook Form + React Compiler: see README

    const { mutateAsync: create, isPending: isCreating } = useCreateGeography();
    const { mutateAsync: update, isPending: isUpdating } = useUpdateGeography();
    const isPending = isCreating || isUpdating;

    const isCity = state?.kind === "city";
    const isEdit = state?.node != null;

    const {
        register,
        handleSubmit,
        reset,
        formState: { errors },
    } = useForm<TFormValues>({
        resolver: zodResolver(isCity ? citySchema : provinceSchema),
    });

    useEffect(() => {
        if (!state) return;
        reset({
            name: state.node?.name ?? "",
            latitude: state.node?.latitude ?? undefined,
            longitude: state.node?.longitude ?? undefined,
            radius_km: state.node?.radius_km ?? undefined,
        });
    }, [state, reset]);

    const onSubmit = handleSubmit(async (values) => {
        if (!state) return;
        const area = isCity
            ? { latitude: values.latitude, longitude: values.longitude, radius_km: values.radius_km }
            : {};

        if (state.node) {
            await update({ id: state.node.id, body: { name: values.name, ...area } });
        } else {
            await create({
                name: values.name,
                level: state.kind,
                parent_id: state.parent.id,
                ...area,
            });
        }
        showToast.success(`${values.name} ${isEdit ? "updated" : "added"}`);
        onClose();
    });

    const title = state
        ? `${isEdit ? "Edit" : "Add"} ${state.kind === "city" ? "city" : "province"}${!isEdit && state.kind === "city" ? ` in ${state.parent.name}` : ""}`
        : "";

    return (
        <Dialog open={state !== null} onOpenChange={(next) => !next && !isPending && onClose()}>
            <DialogContent>
                <form onSubmit={onSubmit} noValidate className="space-y-4">
                    <DialogHeader>
                        <DialogTitle>{title}</DialogTitle>
                        <DialogDescription>
                            {isCity
                                ? "A search covers the square around the centre, from the centre out to the radius on each side."
                                : "Provinces group cities; each city is searched separately."}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-1.5">
                        <Label htmlFor="loc-name">Name</Label>
                        <Input id="loc-name" aria-invalid={!!errors.name} {...register("name")} />
                        {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
                    </div>

                    {isCity && (
                        <>
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1.5">
                                    <Label htmlFor="loc-lat">Latitude</Label>
                                    <Input
                                        id="loc-lat"
                                        type="number"
                                        step="any"
                                        inputMode="decimal"
                                        placeholder="31.5204"
                                        aria-invalid={!!errors.latitude}
                                        {...register("latitude", { valueAsNumber: true })}
                                    />
                                    {errors.latitude && <p className="text-sm text-destructive">{errors.latitude.message}</p>}
                                </div>
                                <div className="space-y-1.5">
                                    <Label htmlFor="loc-lng">Longitude</Label>
                                    <Input
                                        id="loc-lng"
                                        type="number"
                                        step="any"
                                        inputMode="decimal"
                                        placeholder="74.3587"
                                        aria-invalid={!!errors.longitude}
                                        {...register("longitude", { valueAsNumber: true })}
                                    />
                                    {errors.longitude && <p className="text-sm text-destructive">{errors.longitude.message}</p>}
                                </div>
                            </div>
                            <p className="-mt-2 text-xs text-muted-foreground">
                                In Google Maps, right-click the city centre and click the coordinates at the top of the menu to copy them.{" "}
                                <a
                                    href="https://www.google.com/maps"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-0.5 text-primary hover:underline"
                                >
                                    Open Google Maps
                                    <ExternalLink className="size-3" />
                                </a>
                            </p>

                            <div className="space-y-1.5">
                                <Label htmlFor="loc-radius">Search radius (km)</Label>
                                <Input
                                    id="loc-radius"
                                    type="number"
                                    step="any"
                                    inputMode="decimal"
                                    placeholder="10"
                                    aria-invalid={!!errors.radius_km}
                                    {...register("radius_km", { valueAsNumber: true })}
                                />
                                {errors.radius_km && <p className="text-sm text-destructive">{errors.radius_km.message}</p>}
                                <p className="text-xs text-muted-foreground">
                                    Bigger cities need a bigger radius (Karachi 30, Lahore 20, smaller cities 8 to 12).
                                </p>
                            </div>
                        </>
                    )}

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isPending}>
                            {isPending && <Loader2 className="animate-spin" />}
                            {isEdit ? "Save changes" : "Add"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default LocationDialog;
