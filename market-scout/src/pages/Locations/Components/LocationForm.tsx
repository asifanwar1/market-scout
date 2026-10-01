"use no memo";

import { zodResolver } from "@hookform/resolvers/zod";
import { ExternalLink, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateGeography, useUpdateGeography } from "@/hooks/api/geographies.queries";
import { showToast } from "@/lib/toast";
import {
    GOOGLE_MAPS_URL,
    LOCATION_KIND,
    LOCATION_LATITUDE_ID,
    LOCATION_LONGITUDE_ID,
    LOCATION_NAME_ID,
    LOCATION_RADIUS_ID,
} from "../Locations.constants";
import type { TLocationDialogState, TLocationFormValues } from "../Locations.types";
import { citySchema, provinceSchema } from "./LocationForm.schema";

type TLocationFormProps = {
    state: TLocationDialogState;
    onClose: () => void;
};

const buildLocationFormValues = (state: TLocationDialogState): TLocationFormValues => ({
    name: state.node?.name ?? "",
    latitude: state.node?.latitude ?? undefined,
    longitude: state.node?.longitude ?? undefined,
    radius_km: state.node?.radius_km ?? undefined,
});

const buildAreaPayload = (values: TLocationFormValues, isCity: boolean) =>
    isCity ? { latitude: values.latitude, longitude: values.longitude, radius_km: values.radius_km } : {};

const buildTitle = (state: TLocationDialogState, isEdit: boolean): string => {
    const action = isEdit ? "Edit" : "Add";
    const place = state.kind === LOCATION_KIND.CITY && state.parent ? ` in ${state.parent.name}` : "";
    return `${action} ${state.kind}${place}`;
};

const LocationForm = ({ state, onClose }: TLocationFormProps) => {
    const { mutateAsync: create, isPending: isCreating } = useCreateGeography();
    const { mutateAsync: update, isPending: isUpdating } = useUpdateGeography();
    const isPending = isCreating || isUpdating;

    const isCity = state.kind === LOCATION_KIND.CITY;
    const isEdit = state.node !== null;
    const title = buildTitle(state, isEdit);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<TLocationFormValues>({
        resolver: zodResolver(isCity ? citySchema : provinceSchema),
        defaultValues: buildLocationFormValues(state),
    });

    const onSubmit = handleSubmit(async (values) => {
        const area = buildAreaPayload(values, isCity);

        if (state.node) {
            await update({ id: state.node.id, body: { name: values.name, ...area } });
        } else {
            await create({ name: values.name, level: state.kind, parent_id: state.parent.id, ...area });
        }
        showToast.success(`${values.name} ${isEdit ? "updated" : "added"}`);
        onClose();
    });

    return (
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
                <Label htmlFor={LOCATION_NAME_ID}>Name</Label>
                <Input id={LOCATION_NAME_ID} aria-invalid={!!errors.name} {...register("name")} />
                {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>

            {isCity && (
                <>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label htmlFor={LOCATION_LATITUDE_ID}>Latitude</Label>
                            <Input
                                id={LOCATION_LATITUDE_ID}
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
                            <Label htmlFor={LOCATION_LONGITUDE_ID}>Longitude</Label>
                            <Input
                                id={LOCATION_LONGITUDE_ID}
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
                            href={GOOGLE_MAPS_URL}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-0.5 text-primary hover:underline"
                        >
                            Open Google Maps
                            <ExternalLink className="size-3" />
                        </a>
                    </p>

                    <div className="space-y-1.5">
                        <Label htmlFor={LOCATION_RADIUS_ID}>Search radius (km)</Label>
                        <Input
                            id={LOCATION_RADIUS_ID}
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
    );
};

export default LocationForm;
