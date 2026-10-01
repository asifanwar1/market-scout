import { Star, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";

import type { TMovers } from "@/api/services/insights/insights.response.types";
import EmptyState from "@/components/custom/EmptyState";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatCount, formatShortDate } from "@/utils/format.utils";

type TMoversCardProps = {
    movers: TMovers | undefined;
};

const MoversCard = ({ movers }: TMoversCardProps) => {
    const rows = movers?.data ?? [];

    return (
        <Card>
            <CardHeader>
                <CardTitle>Getting busier</CardTitle>
                <CardDescription>
                    Businesses seen in the last {movers?.days ?? 30} days whose customer reviews grew most since the search before. A rough sign of who is winning business.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {rows.length === 0 ? (
                    <EmptyState
                        icon={TrendingUp}
                        title="Nothing has moved yet"
                        description="This fills in once the same area has been searched more than once with a source that reports reviews, such as Google Places."
                    />
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Business</TableHead>
                                <TableHead className="text-right">Reviews</TableHead>
                                <TableHead className="text-right">Change</TableHead>
                                <TableHead className="text-right">Since</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.business_id}>
                                    <TableCell className="font-medium">
                                        <Link to={`${APP_ROUTES.LEADS}?lead=${row.business_id}`} className="hover:underline">
                                            {row.name}
                                        </Link>
                                        {row.city && <span className="block text-xs font-normal text-muted-foreground">{row.city}</span>}
                                    </TableCell>
                                    <TableCell className="text-right tabular-nums">
                                        {formatCount(row.review_count)}
                                        {row.rating !== null && (
                                            <span className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
                                                <Star className="size-3 fill-current text-chart-2" />
                                                {row.rating.toFixed(1)}
                                            </span>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-right font-medium text-success-foreground tabular-nums">+{formatCount(row.review_change)}</TableCell>
                                    <TableCell className="text-right whitespace-nowrap text-muted-foreground">{formatShortDate(row.previous_seen_at)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </CardContent>
        </Card>
    );
};

export default MoversCard;
