import type { TGeographyNode } from "@/api/services/geographies/geographies.response.types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";

type TLocationPickerProps = {
    tree: TGeographyNode[];
    selected: number[];
    onChange: (cityIds: number[]) => void;
};

// Country -> province -> city. Ticking a province ticks every city in it.
const LocationPicker = ({ tree, selected, onChange }: TLocationPickerProps) => {
    const provinces = tree.flatMap((country) => country.children);
    const allCityIds = provinces.flatMap((province) => province.children.map((city) => city.id));
    const selectedSet = new Set(selected);

    const setMany = (ids: number[], on: boolean) => {
        const next = new Set(selected);
        ids.forEach((id) => (on ? next.add(id) : next.delete(id)));
        onChange([...next]);
    };

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground" aria-live="polite">
                    {selected.length} of {allCityIds.length} cities selected
                </p>
                <div className="flex gap-1">
                    <Button variant="ghost" size="xs" onClick={() => onChange(allCityIds)}>
                        Select all
                    </Button>
                    <Button variant="ghost" size="xs" onClick={() => onChange([])} disabled={selected.length === 0}>
                        Clear
                    </Button>
                </div>
            </div>

            <ScrollArea className="h-80 rounded-lg border">
                <div className="space-y-4 p-4">
                    {provinces.map((province) => {
                        const cityIds = province.children.map((city) => city.id);
                        const selectedCount = cityIds.filter((id) => selectedSet.has(id)).length;
                        const provinceState =
                            selectedCount === cityIds.length ? true : selectedCount > 0 ? "indeterminate" : false;

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
                                    {province.children.map((city) => (
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
                                    ))}
                                </div>
                            </fieldset>
                        );
                    })}
                </div>
            </ScrollArea>
        </div>
    );
};

export default LocationPicker;
