import { Radar, SearchX, UserX } from "lucide-react";
import { Link } from "react-router-dom";

import EmptyState from "@/components/custom/EmptyState";
import { Button } from "@/components/ui/button";
import { APP_ROUTES } from "@/routes/appRoutes";
import { EMPTY_KIND } from "../Leads.constants";
import type { TEmptyKind } from "../Leads.types";

type TLeadsEmptyStateProps = {
    kind: TEmptyKind;
    isAdmin: boolean;
    onClearFilters: () => void;
};

const LeadsEmptyState = ({ kind, isAdmin, onClearFilters }: TLeadsEmptyStateProps) => {
    if (kind === EMPTY_KIND.NO_PROFILE) {
        return (
            <EmptyState
                icon={UserX}
                title="No profile to search yet"
                description="Leads are organised by profile (an industry such as solar). An administrator needs to set one up first."
            />
        );
    }

    if (kind === EMPTY_KIND.FILTERED) {
        return (
            <EmptyState
                icon={SearchX}
                title="No leads match these filters"
                description="Try removing a filter or searching for something else."
                action={
                    <Button variant="outline" onClick={onClearFilters}>
                        Clear filters
                    </Button>
                }
            />
        );
    }

    return (
        <EmptyState
            icon={Radar}
            title="No leads yet"
            description={
                isAdmin
                    ? "Start a run to search for businesses in the cities you sell in."
                    : "Leads appear here once an administrator has run a search."
            }
            action={
                isAdmin ? (
                    <Button asChild>
                        <Link to={APP_ROUTES.RUNS_NEW}>Start a run</Link>
                    </Button>
                ) : undefined
            }
        />
    );
};

export default LeadsEmptyState;
