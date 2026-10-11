import { Loader2, ScanSearch } from "lucide-react";
import { useState } from "react";

import type { TDuplicate, TDuplicateSide } from "@/api/services/quality/quality.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import Loading from "@/components/custom/Loading";
import Pagination from "@/components/custom/Pagination";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ACTIVE_QUALITY_TASK_STATUSES, DUPLICATE_CONFIDENCE, DUPLICATE_REASON_LABELS } from "@/constants/quality.constants";
import {
    useDismissDuplicate,
    useGetDuplicates,
    useGetQualityTask,
    useMergeDuplicate,
    useScanDuplicates,
} from "@/hooks/api/quality.queries";
import { showToast } from "@/lib/toast";
import { FIRST_PAGE } from "@/constants";
import {
    DUPLICATES_DESCRIPTION,
    DUPLICATES_EMPTY,
    DUPLICATES_TITLE,
    MERGE_DESCRIPTION,
    MERGE_TITLE,
    PAGE_SIZE,
    SCAN_HELP,
    SCAN_LABEL,
    SIDE_LABELS,
} from "../Quality.constants";
import DuplicateSide from "./DuplicateSide";

type TPendingMerge = {
    candidate: TDuplicate;
    keep: TDuplicateSide;
};

const DuplicatesCard = () => {
    const [page, setPage] = useState(FIRST_PAGE);
    const [pendingMerge, setPendingMerge] = useState<TPendingMerge | null>(null);
    const [scanId, setScanId] = useState<number | null>(null);

    const { data, isPending } = useGetDuplicates({ page, limit: PAGE_SIZE });
    const { mutateAsync: scan, isPending: isStartingScan } = useScanDuplicates();
    const { mutateAsync: merge, isPending: isMerging } = useMergeDuplicate();
    const { mutateAsync: dismiss, isPending: isDismissing } = useDismissDuplicate();
    const { data: scanTask } = useGetQualityTask(scanId);

    const candidates = data?.data ?? [];
    const total = data?.count ?? 0;
    const isBusy = isMerging || isDismissing;
    const isScanning = isStartingScan || (scanTask !== undefined && ACTIVE_QUALITY_TASK_STATUSES.includes(scanTask.status));

    const startScan = async () => {
        const task = await scan();
        setScanId(task.id);
    };

    const askMerge = (candidate: TDuplicate, keep: TDuplicateSide) => {
        setPendingMerge({ candidate, keep });
    };

    const closeMerge = () => {
        setPendingMerge(null);
    };

    const confirmMerge = async () => {
        if (!pendingMerge) return;
        await merge({ id: pendingMerge.candidate.id, body: { keep_id: pendingMerge.keep.id } });
        showToast.success("Leads merged");
        setPendingMerge(null);
    };

    const notTheSame = async (candidate: TDuplicate) => {
        await dismiss(candidate.id);
        showToast.success("Marked as different businesses");
    };

    const renderCandidate = (candidate: TDuplicate) => (
        <li key={candidate.id} className="space-y-3 px-4 py-4">
            <div className="flex flex-wrap items-center gap-2 text-sm">
                <Badge variant="secondary">
                    {candidate.confidence === DUPLICATE_CONFIDENCE.LIKELY ? "Likely the same" : "Possibly the same"}
                </Badge>
                <span className="text-muted-foreground">{DUPLICATE_REASON_LABELS[candidate.reason] ?? candidate.reason}</span>
                <Button className="ml-auto" size="sm" variant="ghost" disabled={isBusy} onClick={() => notTheSame(candidate)}>
                    Not the same
                </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
                <DuplicateSide label={SIDE_LABELS.a} side={candidate.a} isBusy={isBusy} onKeep={(side) => askMerge(candidate, side)} />
                <DuplicateSide label={SIDE_LABELS.b} side={candidate.b} isBusy={isBusy} onKeep={(side) => askMerge(candidate, side)} />
            </div>
        </li>
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>
                    {DUPLICATES_TITLE}
                    {total > 0 && <span className="ml-2 text-sm font-normal text-muted-foreground">({total})</span>}
                </CardTitle>
                <CardDescription>{DUPLICATES_DESCRIPTION}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                    <Button variant="outline" disabled={isScanning} onClick={startScan}>
                        {isScanning ? <Loader2 className="animate-spin" /> : <ScanSearch />}
                        {SCAN_LABEL}
                    </Button>
                    <p className="text-xs text-muted-foreground">
                        {scanTask && !ACTIVE_QUALITY_TASK_STATUSES.includes(scanTask.status)
                            ? `Looked through ${scanTask.counts.businesses ?? 0} leads and found ${scanTask.counts.pairs_found ?? 0} new pairs.`
                            : SCAN_HELP}
                    </p>
                </div>

                {isPending ? (
                    <Loading />
                ) : total === 0 ? (
                    <p className="text-sm text-muted-foreground">{DUPLICATES_EMPTY}</p>
                ) : (
                    <ul className="divide-y rounded-md border">{candidates.map(renderCandidate)}</ul>
                )}

                {total > PAGE_SIZE && (
                    <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
                )}
            </CardContent>

            <ConfirmationModal
                open={pendingMerge !== null}
                title={MERGE_TITLE}
                description={`${MERGE_DESCRIPTION} Keeping: ${pendingMerge?.keep.name ?? ""}.`}
                confirmText="Merge"
                destructive
                isLoading={isMerging}
                onConfirm={confirmMerge}
                onClose={closeMerge}
            />
        </Card>
    );
};

export default DuplicatesCard;
