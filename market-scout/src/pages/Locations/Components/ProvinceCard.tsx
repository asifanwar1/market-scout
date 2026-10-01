import { Pencil, Plus, Trash2 } from "lucide-react";

import type { TGeographyNode } from "@/api/services/geographies/geographies.response.types";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { COORDINATE_DISPLAY_DIGITS } from "../Locations.constants";

type TProvinceCardProps = {
    province: TGeographyNode;
    onAddCity: (province: TGeographyNode) => void;
    onEditProvince: (province: TGeographyNode) => void;
    onEditCity: (city: TGeographyNode) => void;
    onDelete: (node: TGeographyNode) => void;
};

const ProvinceCard = ({ province, onAddCity, onEditProvince, onEditCity, onDelete }: TProvinceCardProps) => {
    const cityCount = province.children.length;
    const hasCities = cityCount > 0;

    const renderCity = (city: TGeographyNode) => (
        <TableRow key={city.id}>
            <TableCell className="font-medium">{city.name}</TableCell>
            <TableCell className="tabular-nums text-muted-foreground">
                {city.latitude?.toFixed(COORDINATE_DISPLAY_DIGITS)}, {city.longitude?.toFixed(COORDINATE_DISPLAY_DIGITS)}
            </TableCell>
            <TableCell className="text-right tabular-nums">{city.radius_km} km</TableCell>
            <TableCell>
                <div className="flex justify-end gap-1">
                    <Button variant="ghost" size="icon-sm" aria-label={`Edit ${city.name}`} onClick={() => onEditCity(city)}>
                        <Pencil />
                    </Button>
                    <Button variant="ghost" size="icon-sm" aria-label={`Delete ${city.name}`} onClick={() => onDelete(city)}>
                        <Trash2 />
                    </Button>
                </div>
            </TableCell>
        </TableRow>
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-baseline gap-2">
                    {province.name}
                    <span className="text-sm font-normal text-muted-foreground">
                        {cityCount} {cityCount === 1 ? "city" : "cities"}
                    </span>
                </CardTitle>
                <CardAction className="flex items-center gap-1">
                    <Button variant="outline" size="sm" onClick={() => onAddCity(province)}>
                        <Plus />
                        Add city
                    </Button>
                    <Button variant="ghost" size="icon-sm" aria-label={`Rename ${province.name}`} onClick={() => onEditProvince(province)}>
                        <Pencil />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Delete ${province.name}`}
                        disabled={hasCities}
                        title={hasCities ? "Delete its cities first" : undefined}
                        onClick={() => onDelete(province)}
                    >
                        <Trash2 />
                    </Button>
                </CardAction>
            </CardHeader>
            {hasCities && (
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
                        <TableBody>{province.children.map(renderCity)}</TableBody>
                    </Table>
                </CardContent>
            )}
        </Card>
    );
};

export default ProvinceCard;
