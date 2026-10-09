import { TrendingUp } from "lucide-react";

import type { TConversion, TConversionRow } from "@/api/services/insights/insights.response.types";
import EmptyState from "@/components/custom/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CONVERSION_GROUP_OPTIONS } from "@/constants/pipeline.constants";
import { formatCount } from "@/utils/format.utils";
import { formatMoney, formatPercent } from "@/utils/pipeline.utils";
import type { TInsightsPage } from "../Insights.Container";

const TITLE = "What turns into customers";
const DESCRIPTION =
    "Leads that reached each stage, and what closed, grouped by where they came from, their segment or their city. A lead found by two sources counts under both.";
const EMPTY_TITLE = "Nothing to compare yet";
const EMPTY_DESCRIPTION = "Once leads move through the pipeline, you can see which source, segment or city produces customers.";

type TConversionCardProps = {
    page: TInsightsPage;
    conversion: TConversion | undefined;
};

const ConversionCard = ({ page, conversion }: TConversionCardProps) => {
    const { conversionGroup, onConversionGroupChange, currency } = page;
    const rows = conversion?.data ?? [];

    const renderGroup = (option: (typeof CONVERSION_GROUP_OPTIONS)[number]) => (
        <Button
            key={option.value}
            size="sm"
            variant={conversionGroup === option.value ? "default" : "outline"}
            aria-pressed={conversionGroup === option.value}
            onClick={() => onConversionGroupChange(option.value)}
        >
            {option.label}
        </Button>
    );

    const renderRow = (row: TConversionRow) => (
        <TableRow key={row.key}>
            <TableCell className="font-medium whitespace-nowrap">{row.name}</TableCell>
            <TableCell className="text-right tabular-nums">{formatCount(row.leads)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatCount(row.contacted)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatCount(row.interested)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatCount(row.meeting)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatCount(row.quoted)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatCount(row.won)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatCount(row.lost)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatPercent(row.win_rate)}</TableCell>
            <TableCell className="text-right whitespace-nowrap tabular-nums">{formatMoney(row.revenue, currency)}</TableCell>
        </TableRow>
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>{TITLE}</CardTitle>
                <CardDescription>{DESCRIPTION}</CardDescription>
                <CardAction className="flex gap-2">{CONVERSION_GROUP_OPTIONS.map(renderGroup)}</CardAction>
            </CardHeader>
            <CardContent>
                {rows.length === 0 ? (
                    <EmptyState icon={TrendingUp} title={EMPTY_TITLE} description={EMPTY_DESCRIPTION} />
                ) : (
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Group</TableHead>
                                    <TableHead className="text-right">Leads</TableHead>
                                    <TableHead className="text-right">Contacted</TableHead>
                                    <TableHead className="text-right">Interested</TableHead>
                                    <TableHead className="text-right">Meeting</TableHead>
                                    <TableHead className="text-right">Quoted</TableHead>
                                    <TableHead className="text-right">Won</TableHead>
                                    <TableHead className="text-right">Lost</TableHead>
                                    <TableHead className="text-right">Win rate</TableHead>
                                    <TableHead className="text-right">Revenue</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>{rows.map(renderRow)}</TableBody>
                        </Table>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default ConversionCard;
