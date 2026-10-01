import { CheckCircle2, Search } from "lucide-react";
import { Link } from "react-router-dom";

import type { TGapCity, TGaps } from "@/api/services/insights/insights.response.types";
import StatusBadge from "@/components/custom/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { USER_ROLE } from "@/constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { useStore } from "@/store";
import { formatRelative, pluralize } from "@/utils/format.utils";
import { joinNames } from "@/utils/insights.utils";
import type { TInsightsPage } from "../Insights.Container";
import { GAP_REASON } from "@/constants/source.constants";
import { GAP_THRESHOLD_MAX, GAP_THRESHOLD_MIN } from "../Insights.constants";

type TGapsCardProps = {
    page: TInsightsPage;
    gaps: TGaps | undefined;
};

const MAX_SHOWN = 12;

const GapRow = ({ gap, canRun }: { gap: TGapCity; canRun: boolean }) => (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 py-3">
        <div className="min-w-0 space-y-1">
            <p className="flex flex-wrap items-center gap-2 font-medium">
                {gap.city}
                {gap.province && <span className="text-xs font-normal text-muted-foreground">{gap.province}</span>}
                {gap.reason === GAP_REASON.NEVER_SEARCHED ? (
                    <StatusBadge label="Never searched" className="bg-warning text-warning-foreground" />
                ) : (
                    <StatusBadge label="Searched, little found" className="bg-muted text-muted-foreground" />
                )}
            </p>
            <p className="text-sm text-muted-foreground">
                {pluralize(gap.total, "lead", "leads")}
                {gap.reason === GAP_REASON.FEW_FOUND && gap.last_searched_at && ` · last searched ${formatRelative(gap.last_searched_at)}`}
                {gap.missing_segments.length > 0 && gap.total > 0 && ` · no ${joinNames(gap.missing_segments).toLowerCase()} yet`}
            </p>
        </div>
        {canRun && (
            <Button asChild variant="outline" size="sm">
                <Link to={`${APP_ROUTES.RUNS_NEW}?city=${gap.geography_id}`}>
                    <Search />
                    Search here
                </Link>
            </Button>
        )}
    </li>
);

const GapsCard = ({ page, gaps }: TGapsCardProps) => {
    const isAdmin = useStore((state) => state.user?.role === USER_ROLE.ADMIN);
    const list = gaps?.data ?? [];
    const shown = list.slice(0, MAX_SHOWN);

    const renderGap = (gap: (typeof shown)[number]) => (
        <GapRow key={gap.geography_id} gap={gap} canRun={isAdmin} />
    );
    return (
        <Card>
            <CardHeader>
                <CardTitle>Where to look next</CardTitle>
                <CardDescription>Cities in your target list with few leads, places nobody has searched yet first.</CardDescription>
                <CardAction className="flex items-center gap-2">
                    <Label htmlFor="gap-threshold" className="text-sm font-normal whitespace-nowrap">
                        Fewer than
                    </Label>
                    <Input
                        id="gap-threshold"
                        type="number"
                        min={GAP_THRESHOLD_MIN}
                        max={GAP_THRESHOLD_MAX}
                        value={page.threshold}
                        onChange={(event) => {
                            const value = Math.floor(Number(event.target.value));
                            if (value >= GAP_THRESHOLD_MIN && value <= GAP_THRESHOLD_MAX) page.setThreshold(value);
                        }}
                        className="w-20"
                    />
                    <span className="text-sm text-muted-foreground">leads</span>
                </CardAction>
            </CardHeader>
            <CardContent>
                {gaps && list.length === 0 ? (
                    <p className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
                        <CheckCircle2 className="size-4 text-success-foreground" />
                        Every city has at least {pluralize(page.threshold, "lead", "leads")}. Raise the number to look for thinner spots.
                    </p>
                ) : (
                    <>
                        <ul className="divide-y">
                            {shown.map(renderGap)}
                        </ul>
                        {list.length > shown.length && (
                            <p className="pt-3 text-xs text-muted-foreground">And {list.length - shown.length} more cities below this number.</p>
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    );
};

export default GapsCard;
