import { TrendingUp } from "lucide-react";
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { TTimeline } from "@/api/services/insights/insights.response.types";
import EmptyState from "@/components/custom/EmptyState";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatCount } from "@/utils/format.utils";
import { periodLabel } from "@/utils/insights.utils";
import { RANGES } from "../Insights.constants";
import type { TInsightsPage } from "../Insights.Container";

type TGrowthChartProps = {
    page: TInsightsPage;
    timeline: TTimeline | undefined;
};

const AXIS_TICK = { fontSize: 12, fill: "var(--muted-foreground)" };

const GrowthChart = ({ page, timeline }: TGrowthChartProps) => {
    const points = timeline?.data ?? [];
    const hasData = points.some((point) => point.new > 0) || (points.at(-1)?.total ?? 0) > 0;
    const bucket = timeline?.bucket ?? page.range.bucket;

    const renderRange = (range: (typeof RANGES)[number]) => (
        <SelectItem key={range.value} value={range.value}>
            {range.label}
        </SelectItem>
    );
    return (
        <Card>
            <CardHeader>
                <CardTitle>Leads over time</CardTitle>
                <CardDescription>New businesses found each {bucket} (bars) and the running total (line).</CardDescription>
                <CardAction>
                    <Select value={page.range.value} onValueChange={page.setRangeValue}>
                        <SelectTrigger className="w-40" aria-label="Time range">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {RANGES.map(renderRange)}
                        </SelectContent>
                    </Select>
                </CardAction>
            </CardHeader>
            <CardContent>
                {!hasData ? (
                    <EmptyState icon={TrendingUp} title="Nothing to chart yet" description="Once a run finds businesses, their arrival shows up here." />
                ) : (
                    <div className="h-64 w-full" role="img" aria-label="Chart of new leads per period and the running total">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                                <CartesianGrid vertical={false} stroke="var(--border)" />
                                <XAxis
                                    dataKey="period"
                                    tickFormatter={(value: string) => periodLabel(value, bucket)}
                                    tick={AXIS_TICK}
                                    tickLine={false}
                                    axisLine={false}
                                    minTickGap={24}
                                />
                                <YAxis yAxisId="new" allowDecimals={false} width={36} tick={AXIS_TICK} tickLine={false} axisLine={false} />
                                <YAxis
                                    yAxisId="total"
                                    orientation="right"
                                    allowDecimals={false}
                                    width={44}
                                    tick={AXIS_TICK}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <Tooltip
                                    labelFormatter={(value) => periodLabel(String(value), bucket)}
                                    formatter={(value, name) => [formatCount(Number(value)), name === "new" ? "New leads" : "Total leads"]}
                                    contentStyle={{
                                        borderRadius: 8,
                                        border: "1px solid var(--border)",
                                        background: "var(--popover)",
                                        color: "var(--popover-foreground)",
                                    }}
                                />
                                <Bar yAxisId="new" dataKey="new" fill="var(--chart-1)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                                <Line yAxisId="total" dataKey="total" type="monotone" stroke="var(--chart-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default GrowthChart;
