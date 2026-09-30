import { MapPin, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import type { TGeographyNode } from "@/api/services/geographies/geographies.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { useDeleteGeography } from "@/hooks/api/geographies.queries";
import { useGetGeographyTree } from "@/hooks/api/catalog.queries";
import { showToast } from "@/lib/toast";
import LocationDialog, { type TLocationDialogState } from "./LocationDialog";

const Locations = () => {
    const { data: tree = [], isPending } = useGetGeographyTree();
    const { mutateAsync: deleteGeography, isPending: isDeleting } = useDeleteGeography();

    const [dialog, setDialog] = useState<TLocationDialogState | null>(null);
    const [toDelete, setToDelete] = useState<TGeographyNode | null>(null);

    const country = tree[0];
    const provinces = tree.flatMap((node) => node.children);

    const confirmDelete = async () => {
        if (!toDelete) return;
        await deleteGeography(toDelete.id);
        showToast.success(`${toDelete.name} deleted`);
        setToDelete(null);
    };

    if (isPending) return <Loading />;

    return (
        <div className="space-y-6">
            <PageHeader
                title="Locations"
                description="The cities a run can search. Each city's centre and radius decide the area that is covered."
                actions={
                    country && (
                        <Button onClick={() => setDialog({ kind: "province", node: null, parent: country })}>
                            <Plus />
                            Add province
                        </Button>
                    )
                }
            />

            {provinces.length === 0 && (
                <EmptyState
                    icon={MapPin}
                    title="No locations yet"
                    description="Load the defaults with `python -m scripts.seed` on the server, or add locations here."
                />
            )}

            {provinces.map((province) => (
                <Card key={province.id}>
                    <CardHeader>
                        <CardTitle className="flex items-baseline gap-2">
                            {province.name}
                            <span className="text-sm font-normal text-muted-foreground">
                                {province.children.length} {province.children.length === 1 ? "city" : "cities"}
                            </span>
                        </CardTitle>
                        <CardAction className="flex items-center gap-1">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setDialog({ kind: "city", node: null, parent: province })}
                            >
                                <Plus />
                                Add city
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon-sm"
                                aria-label={`Rename ${province.name}`}
                                onClick={() => setDialog({ kind: "province", node: province, parent: null })}
                            >
                                <Pencil />
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon-sm"
                                aria-label={`Delete ${province.name}`}
                                disabled={province.children.length > 0}
                                title={province.children.length > 0 ? "Delete its cities first" : undefined}
                                onClick={() => setToDelete(province)}
                            >
                                <Trash2 />
                            </Button>
                        </CardAction>
                    </CardHeader>
                    {province.children.length > 0 && (
                        <CardContent className="p-0">
                            <Table>
                                <TableHeader className="bg-muted/40">
                                    <TableRow className="hover:bg-transparent">
                                        <TableHead>City</TableHead>
                                        <TableHead>Centre (latitude, longitude)</TableHead>
                                        <TableHead className="text-right">Radius</TableHead>
                                        <TableHead className="w-24" />
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {province.children.map((city) => (
                                        <TableRow key={city.id}>
                                            <TableCell className="font-medium">{city.name}</TableCell>
                                            <TableCell className="tabular-nums text-muted-foreground">
                                                {city.latitude?.toFixed(4)}, {city.longitude?.toFixed(4)}
                                            </TableCell>
                                            <TableCell className="text-right tabular-nums">{city.radius_km} km</TableCell>
                                            <TableCell>
                                                <div className="flex justify-end gap-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="icon-sm"
                                                        aria-label={`Edit ${city.name}`}
                                                        onClick={() => setDialog({ kind: "city", node: city, parent: null })}
                                                    >
                                                        <Pencil />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="icon-sm"
                                                        aria-label={`Delete ${city.name}`}
                                                        onClick={() => setToDelete(city)}
                                                    >
                                                        <Trash2 />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </CardContent>
                    )}
                </Card>
            ))}

            <LocationDialog state={dialog} onClose={() => setDialog(null)} />

            <ConfirmationModal
                open={toDelete !== null}
                destructive
                title={`Delete ${toDelete?.name ?? ""}?`}
                description={
                    toDelete?.level === "city"
                        ? "Leads already found there are kept but no longer show a city. Past runs keep its name."
                        : "This province has no cities left, so nothing else is affected."
                }
                confirmText="Delete"
                isLoading={isDeleting}
                onConfirm={confirmDelete}
                onClose={() => setToDelete(null)}
            />
        </div>
    );
};

export default Locations;
