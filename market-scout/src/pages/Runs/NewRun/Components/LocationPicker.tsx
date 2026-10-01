import { Search } from "lucide-react";
import { useState } from "react";

import type { TGeographyNode } from "@/api/services/geographies/geographies.response.types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";

type TLocationPickerProps = {
    tree: TGeographyNode[];
    selected: number[];
    onChange: (cityIds: number[]) => void;
};

const LocationPicker = ({ tree, selected, onChange }: TLocationPickerProps) => {
    const [search, setSearch] = useState("");
    const needle = search.trim().toLowerCase();

    const allProvinces = tree.flatMap((country) => country.children);
    const allCityIds = allProvinces.flatMap((province) => province.children.map((city) => city.id));
    const provinces = allProvinces
        .map((province) => ({
            ...province,
            children: needle ? province.children.filter((city) => city.name.toLowerCase().includes(needle)) : province.children,
        }))
        .filter((province) => province.children.length > 0);
    const shownCityIds = provinces.flatMap((province) => province.children.map((city) => city.id));
    const selectedSet = new Set(selected);

    const setMany = (ids: number[], on: boolean) => {
        const next = new Set(selected);
        ids.forEach((id) => (on ? next.add(id) : next.delete(id)));
        onChange([...next]);
    };

    const renderProvince = (province: (typeof provinces)[number]) => {
        const cityIds = province.children.map((city) => city.id);
        const selectedCount = cityIds.filter((id) => selectedSet.has(id)).length;
        const provinceState =
            selectedCount === cityIds.length ? true : selectedCount > 0 ? "indeterminate" : false;

        const renderCity = (city: (typeof province.children)[number]) => (
            <div key={city.id} className="flex items-center gap-2">
                <Checkbox
                    id={`city-${city.id}`}
                    checked={selectedSet.has(city.id)}
                    onCheckedChange={(checked) => setMany([city.id], checked === true)}
                />
                <Label htmlFor={`city-${city.id}`} className="font-normal">
                    {city.name}
                </Label>
            </div>
        );
        return (
            <fieldset key={province.id} className="space-y-2">
                <div className="flex items-center gap-2">
                    <Checkbox
                        id={`province-${province.id}`}
                        checked={provinceState}
                        onCheckedChange={(checked) => setMany(cityIds, checked === true)}
                    />
                    <Label htmlFor={`province-${province.id}`} className="font-semibold">
                        {province.name}
                        <span className="ml-1.5 font-normal text-muted-foreground">
                            {selectedCount}/{cityIds.length}
                        </span>
                    </Label>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 pl-6 sm:grid-cols-3">
                    {province.children.map(renderCity)}
                </div>
            </fieldset>
        );
    };
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground" aria-live="polite">
                    {selected.length} of {allCityIds.length} cities selected
                </p>
                <div className="flex gap-1">
                    <Button variant="ghost" size="xs" onClick={() => setMany(shownCityIds, true)}>
                        {needle ? "Select shown" : "Select all"}
                    </Button>
                    <Button variant="ghost" size="xs" onClick={() => onChange([])} disabled={selected.length === 0}>
                        Clear
                    </Button>
                </div>
            </div>

            <div className="relative">
                <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                    type="search"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Find a city"
                    aria-label="Find a city"
                    className="pl-8"
                />
            </div>

            <ScrollArea className="h-80 rounded-lg border">
                <div className="space-y-4 p-4">
                    {provinces.length === 0 && (
                        <p className="py-8 text-center text-sm text-muted-foreground">No city matches "{search.trim()}".</p>
                    )}
                    {provinces.map(renderProvince)}
                </div>
            </ScrollArea>
        </div>
    );
};

export default LocationPicker;
