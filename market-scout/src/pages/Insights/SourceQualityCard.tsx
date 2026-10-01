import { Plug } from "lucide-react";

import type { TSourcesQuality } from "@/api/services/insights/insights.response.types";
import EmptyState from "@/components/custom/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCount, formatUsd } from "@/utils/format.utils";
import { percent } from "@/utils/insights.utils";

type TSourceQualityCardProps = {
    sources: TSourcesQuality | undefined;
};

const SourceQualityCard = ({ sources }: TSourceQualityCardProps) => {
    const rows = sources?.data ?? [];
    const paid = rows.find((row) => row.is_paid && row.estimated_cost_usd !== null);

    return (
        <Card>
            <CardHeader>
                <CardTitle>Which source is worth it</CardTitle>
                <CardDescription>
                    What each source has delivered. "Only this source" counts leads no other search source found, which is what a source adds on its own.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {rows.length === 0 ? (
                    <EmptyState icon={Plug} title="No source has found anything yet" description="Compare the free and paid sources here after a run or two." />
                ) : (
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Source</TableHead>
                                    <TableHead className="text-right">Leads</TableHead>
                                    <TableHead className="text-right">Only this source</TableHead>
                                    <TableHead className="text-right">With phone</TableHead>
                                    <TableHead className="text-right">WhatsApp</TableHead>
                                    <TableHead className="text-right">With email</TableHead>
                                    <TableHead className="text-right">With website</TableHead>
                                    <TableHead className="text-right">Cost</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {rows.map((row) => (
                                    <TableRow key={row.key}>
                                        <TableCell className="font-medium whitespace-nowrap">
                                            {row.name}{" "}
                                            <Badge variant={row.is_paid ? "secondary" : "outline"} className="ml-1 font-normal">
                                                {row.is_paid ? "Paid" : row.kind === "enrichment" ? "Adds contacts" : "Free"}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right tabular-nums">{formatCount(row.found)}</TableCell>
                                        <TableCell className="text-right tabular-nums">{row.exclusive === null ? "—" : formatCount(row.exclusive)}</TableCell>
                                        <TableCell className="text-right tabular-nums">{percent(row.with_phone, row.found)}</TableCell>
                                        <TableCell className="text-right tabular-nums">{percent(row.with_whatsapp, row.found)}</TableCell>
                                        <TableCell className="text-right tabular-nums">{percent(row.with_email, row.found)}</TableCell>
                                        <TableCell className="text-right tabular-nums">{percent(row.with_website, row.found)}</TableCell>
                                        <TableCell className="text-right whitespace-nowrap tabular-nums">
                                            {row.estimated_cost_usd === null
                                                ? "Free"
                                                : `${formatUsd(row.estimated_cost_usd)}${row.cost_per_lead_usd !== null ? ` · ${formatUsd(row.cost_per_lead_usd)}/lead` : ""}`}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                )}
                {paid && (
                    <p className="mt-3 text-xs text-muted-foreground">Paid costs are estimates from the number of billable requests made, not a bill.</p>
                )}
            </CardContent>
        </Card>
    );
};

export default SourceQualityCard;
