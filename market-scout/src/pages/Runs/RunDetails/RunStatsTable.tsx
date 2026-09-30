import type { TRun } from "@/api/services/runs/runs.response.types";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { formatCount, getSourceLabel } from "@/utils/format.utils";

const pct = (part: number, whole: number) =>
    whole === 0 ? "—" : `${Math.round((100 * part) / whole)}%`;

type TRunStatsTableProps = {
    run: TRun;
};

// One row per source: how many businesses it found and how complete they were. This is the
// comparison that shows whether a paid source is worth it.
const RunStatsTable = ({ run }: TRunStatsTableProps) => {
    const rows = Object.entries(run.stats).filter(([key]) => key !== "website_enrichment");
    const enrichment = run.stats.website_enrichment;

    if (rows.length === 0) {
        return <p className="text-sm text-muted-foreground">No results yet.</p>;
    }

    return (
        <div className="space-y-4">
            <div className="overflow-hidden rounded-lg border">
                <Table>
                    <TableHeader className="bg-muted/40">
                        <TableRow className="hover:bg-transparent">
                            <TableHead>Source</TableHead>
                            <TableHead className="text-right">Searches</TableHead>
                            <TableHead className="text-right">Found</TableHead>
                            <TableHead className="text-right">New</TableHead>
                            <TableHead className="text-right">Already known</TableHead>
                            <TableHead className="text-right">With phone</TableHead>
                            <TableHead className="text-right">With website</TableHead>
                            <TableHead className="text-right">With email</TableHead>
                            <TableHead className="text-right">Requests</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map(([key, stats]) => (
                            <TableRow key={key}>
                                <TableCell className="font-medium">{getSourceLabel(key)}</TableCell>
                                <TableCell className="text-right tabular-nums">
                                    {stats.tasks_done}
                                    {stats.tasks_failed > 0 && (
                                        <span className="text-destructive"> (+{stats.tasks_failed} failed)</span>
                                    )}
                                </TableCell>
                                <TableCell className="text-right tabular-nums">{formatCount(stats.found)}</TableCell>
                                <TableCell className="text-right tabular-nums">{formatCount(stats.new)}</TableCell>
                                <TableCell className="text-right tabular-nums">{formatCount(stats.merged)}</TableCell>
                                <TableCell className="text-right tabular-nums">{pct(stats.with_phone, stats.found)}</TableCell>
                                <TableCell className="text-right tabular-nums">{pct(stats.with_website, stats.found)}</TableCell>
                                <TableCell className="text-right tabular-nums">{pct(stats.with_email, stats.found)}</TableCell>
                                <TableCell className="text-right tabular-nums">{formatCount(stats.requests)}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>

            {rows.some(([, stats]) => stats.blocked > 0) && (
                <p className="text-xs text-muted-foreground">
                    Some results were skipped because those businesses asked not to be contacted.
                </p>
            )}

            {enrichment && (
                <p className="text-sm text-muted-foreground">
                    Website check: read {enrichment.visited} sites, found an email on {enrichment.with_email},
                    a WhatsApp number on {enrichment.with_whatsapp} and a social page on {enrichment.with_social}.
                    {enrichment.failed > 0 && ` ${enrichment.failed} couldn't be read.`}
                    {enrichment.blocked_by_robots > 0 &&
                        ` ${enrichment.blocked_by_robots} asked not to be read.`}
                </p>
            )}
        </div>
    );
};

export default RunStatsTable;
