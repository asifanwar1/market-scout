import type { TOverview } from "@/api/services/insights/insights.response.types";
import { Card, CardContent } from "@/components/ui/card";
import { formatCount } from "@/utils/format.utils";
import { percent } from "@/utils/insights.utils";

type TOverviewCardsProps = {
    overview: TOverview;
};

const Tile = ({ label, value, hint }: { label: string; value: string; hint?: string }) => (
    <Card size="sm">
        <CardContent>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
            {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
        </CardContent>
    </Card>
);

const OverviewCards = ({ overview }: TOverviewCardsProps) => {
    const { total } = overview;

    return (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <Tile label="Leads" value={formatCount(total)} hint={`${formatCount(overview.new_last_7_days)} new this week`} />
            <Tile label="New in 30 days" value={formatCount(overview.new_last_30_days)} />
            <Tile label="Can be called" value={percent(overview.with_phone, total)} hint={`${formatCount(overview.with_phone)} with a phone`} />
            <Tile label="On WhatsApp (likely)" value={percent(overview.whatsapp_likely, total)} hint={`${formatCount(overview.whatsapp_likely)} leads`} />
            <Tile label="Have an email" value={percent(overview.with_email, total)} hint={`${formatCount(overview.with_email)} leads`} />
            <Tile label="Have a website" value={percent(overview.with_website, total)} hint={`${formatCount(overview.with_website)} leads`} />
        </div>
    );
};

export default OverviewCards;
