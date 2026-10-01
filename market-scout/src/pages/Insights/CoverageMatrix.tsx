import { Grid3x3 } from "lucide-react";
import { useState } from "react";

import type { TCoverage } from "@/api/services/insights/insights.response.types";
import EmptyState from "@/components/custom/EmptyState";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { formatCount } from "@/utils/format.utils";
import { heatLevel } from "@/utils/insights.utils";

type TCoverageMatrixProps = {
    coverage: TCoverage | undefined;
};

const SHADES = [
    "text-muted-foreground/60",
    "bg-chart-1/15",
    "bg-chart-1/30",
    "bg-chart-1/50 text-foreground",
    "bg-chart-1/75 text-white",
];

const CoverageMatrix = ({ coverage }: TCoverageMatrixProps) => {
    const [showEmpty, setShowEmpty] = useState(false);

    const segments = coverage?.segments ?? [];
    const allCities = coverage?.cities ?? [];
    const withLeads = allCities.filter((city) => city.total > 0);
    const cities = (showEmpty ? allCities : withLeads)
        .slice()
        .sort((a, b) => b.total - a.total || a.city.localeCompare(b.city));
    const max = Math.max(0, ...allCities.flatMap((city) => segments.map((segment) => city.counts[segment.slug] ?? 0)));

    return (
        <Card>
            <CardHeader>
                <CardTitle>Coverage by city and type</CardTitle>
                <CardDescription>
                    How many leads there are in each city for each kind of business. Darker means more; a dash means none yet.
                </CardDescription>
                <CardAction className="flex items-center gap-2">
                    <Switch id="show-empty" checked={showEmpty} onCheckedChange={setShowEmpty} />
                    <Label htmlFor="show-empty" className="text-sm font-normal">
                        Show cities with none
                    </Label>
                </CardAction>
            </CardHeader>
            <CardContent>
                {withLeads.length === 0 && !showEmpty ? (
                    <EmptyState icon={Grid3x3} title="No leads to map yet" description="Run a search and each city's coverage appears here." />
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full border-separate border-spacing-0.5 text-sm">
                            <thead>
                                <tr>
                                    <th className="px-2 py-1 text-left font-medium">City</th>
                                    {segments.map((segment) => (
                                        <th key={segment.slug} className="px-2 py-1 text-center font-medium">
                                            {segment.name}
                                        </th>
                                    ))}
                                    <th className="px-2 py-1 text-right font-medium">All</th>
                                </tr>
                            </thead>
                            <tbody>
                                {cities.map((city) => (
                                    <tr key={city.geography_id}>
                                        <th scope="row" className="px-2 py-1 text-left font-normal whitespace-nowrap">
                                            {city.city}
                                            {city.province && <span className="ml-1.5 text-xs text-muted-foreground">{city.province}</span>}
                                        </th>
                                        {segments.map((segment) => {
                                            const count = city.counts[segment.slug] ?? 0;
                                            return (
                                                <td
                                                    key={segment.slug}
                                                    className={cn("min-w-14 rounded px-2 py-1 text-center tabular-nums", SHADES[heatLevel(count, max)])}
                                                    title={`${city.city} · ${segment.name}: ${count}`}
                                                >
                                                    {count > 0 ? formatCount(count) : "–"}
                                                </td>
                                            );
                                        })}
                                        <td className="px-2 py-1 text-right font-medium tabular-nums">{formatCount(city.total)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {coverage && coverage.unplaced > 0 && (
                    <p className="mt-3 text-xs text-muted-foreground">{formatCount(coverage.unplaced)} more leads have no city recorded.</p>
                )}
            </CardContent>
        </Card>
    );
};

export default CoverageMatrix;
