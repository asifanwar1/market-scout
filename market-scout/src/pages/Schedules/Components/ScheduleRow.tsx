import { Play, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import type { TSchedule } from "@/api/services/schedules/schedules.response.types";
import StatusBadge from "@/components/custom/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { getRunStatus } from "@/constants/run-status.constants";
import { getScheduleFrequencyLabel } from "@/constants/schedule.constants";
import { APP_ROUTES } from "@/routes/appRoutes";
import { formatUpcoming, getSourceLabel, pluralize } from "@/utils/format.utils";
import { MAX_CITIES_SHOWN, PAUSED_LABEL } from "../Schedules.constants";

type TScheduleRowProps = {
    schedule: TSchedule;
    isBusy: boolean;
    onToggle: (schedule: TSchedule) => void;
    onRunNow: (schedule: TSchedule) => void;
    onDelete: (schedule: TSchedule) => void;
};

const describeCities = (cities: string[]): string => {
    if (cities.length <= MAX_CITIES_SHOWN) return cities.join(", ");
    return `${cities.slice(0, MAX_CITIES_SHOWN).join(", ")} and ${cities.length - MAX_CITIES_SHOWN} more`;
};

const ScheduleRow = ({ schedule, isBusy, onToggle, onRunNow, onDelete }: TScheduleRowProps) => {
    const lastRun = schedule.last_run;
    const lastRunStatus = lastRun ? getRunStatus(lastRun.status) : undefined;
    const runLink = lastRun ? APP_ROUTES.RUNS_DETAILS.replace(":id", String(lastRun.id)) : "";
    const sources = schedule.source_keys.map(getSourceLabel).join(", ");

    return (
        <li className="flex flex-wrap items-start gap-4 px-4 py-4">
            <div className="min-w-0 flex-1 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                    <p className="break-words font-medium">{schedule.name}</p>
                    {!schedule.is_active && <Badge variant="secondary">{PAUSED_LABEL}</Badge>}
                </div>
                <p className="text-xs text-muted-foreground">
                    {schedule.profile_name} · {describeCities(schedule.cities)} · {sources}
                </p>
                <p className="text-xs text-muted-foreground">
                    {getScheduleFrequencyLabel(schedule.frequency)}
                    {schedule.is_active && ` · next run ${formatUpcoming(schedule.next_run_at)}`}
                </p>
                {lastRun && lastRunStatus && (
                    <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>Last run</span>
                        <Link to={runLink} className="font-medium text-foreground hover:underline">
                            Run #{lastRun.id}
                        </Link>
                        <StatusBadge label={lastRunStatus.label} className={lastRunStatus.className} />
                        <span>{pluralize(lastRun.new_leads, "new lead", "new leads")}</span>
                    </p>
                )}
                {schedule.last_error && <p className="break-words text-xs text-destructive">{schedule.last_error}</p>}
            </div>
            <div className="flex items-center gap-2">
                <Switch
                    checked={schedule.is_active}
                    disabled={isBusy}
                    aria-label={schedule.is_active ? `Pause ${schedule.name}` : `Switch on ${schedule.name}`}
                    onCheckedChange={() => onToggle(schedule)}
                />
                <Button variant="outline" size="sm" disabled={isBusy} onClick={() => onRunNow(schedule)}>
                    <Play />
                    Run now
                </Button>
                <Button
                    variant="ghost"
                    size="icon-xs"
                    disabled={isBusy}
                    aria-label={`Delete ${schedule.name}`}
                    onClick={() => onDelete(schedule)}
                >
                    <Trash2 />
                </Button>
            </div>
        </li>
    );
};

export default ScheduleRow;
