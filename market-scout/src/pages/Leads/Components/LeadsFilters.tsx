import { Search, SlidersHorizontal, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectLabel,
    SelectSeparator,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { ALL_OPTION_VALUE, LEAD_STATUS_OPTIONS } from "@/constants";
import { getSourceLabel } from "@/utils/format.utils";
import { useStore } from "@/store";
import type { TSegment } from "@/api/services/profiles/profiles.response.types";
import { FILTER_FLAGS, MIN_SCORES, UNASSIGNED } from "../Leads.constants";
import type { TLeadsPage } from "../Leads.Container";

type TLeadsFiltersProps = {
    page: TLeadsPage;
};

const LeadsFilters = ({ page }: TLeadsFiltersProps) => {
    const {
        state,
        searchText,
        onSearchChange,
        profiles,
        activeProfileId,
        profile,
        geographyTree,
        assignees,
        sources,
        changeFilters,
        clearFilters,
        activeFilterCount,
    } = page;
    const currentUserId = useStore((store) => store.user?.id);

    const moreFilterCount = [
        state.phone,
        state.whatsapp,
        state.email,
        state.website,
        state.minScore,
    ].filter(Boolean).length;

    const provinces = geographyTree.flatMap((country) => country.children);

    const renderMinScoreOption = (option: (typeof MIN_SCORES)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );
    const renderFlag = ([key, label]: (typeof FILTER_FLAGS)[number]) => (
        <div key={key} className="flex items-center gap-2">
            <Checkbox
                id={`filter-${key}`}
                checked={!!state[key]}
                onCheckedChange={(checked) =>
                    changeFilters({ [key]: checked === true ? true : null })
                }
            />
            <Label htmlFor={`filter-${key}`}>{label}</Label>
        </div>
    );
    const renderSource = (source: (typeof sources)[number]) => (
        <SelectItem key={source.key} value={source.key}>
            {source.name}
        </SelectItem>
    );
    const renderUser = (user: (typeof assignees)[number]) => (
        <SelectItem key={user.id} value={String(user.id)}>
            {user.full_name}
            {user.id === currentUserId ? " (me)" : ""}
        </SelectItem>
    );
    const renderStatusOption = (option: (typeof LEAD_STATUS_OPTIONS)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );
    const renderSegment = (segment: TSegment) => (
        <SelectItem key={segment.id} value={segment.slug}>
            {segment.name}
        </SelectItem>
    );
    const renderProfile = (item: (typeof profiles)[number]) => (
        <SelectItem key={item.id} value={String(item.id)}>
            {item.name}
        </SelectItem>
    );
    const renderProvince = (province: (typeof provinces)[number]) => {
        const renderCity = (city: (typeof province.children)[number]) => (
            <SelectItem key={city.id} value={String(city.id)}>
                {city.name}
            </SelectItem>
        );
        return (
            <SelectGroup key={province.id}>
                <SelectSeparator />
                <SelectLabel>{province.name}</SelectLabel>
                <SelectItem value={String(province.id)}>
                    All of {province.name}
                </SelectItem>
                {province.children.map(renderCity)}
            </SelectGroup>
        );
    };
    return (
        <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-56 flex-1 sm:max-w-xs">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        value={searchText}
                        onChange={onSearchChange}
                        placeholder="Search name, phone, email, address…"
                        aria-label="Search leads"
                        className="pl-8"
                    />
                </div>

                {profiles.length > 1 && (
                    <Select
                        value={activeProfileId ? String(activeProfileId) : ""}
                        onValueChange={(value) =>
                            changeFilters({ profile: Number(value), segment: null })
                        }
                    >
                        <SelectTrigger className="w-48" aria-label="Profile">
                            <SelectValue placeholder="Profile" />
                        </SelectTrigger>
                        <SelectContent>
                            {profiles.map(renderProfile)}
                        </SelectContent>
                    </Select>
                )}

                <Select
                    value={state.segment ?? ALL_OPTION_VALUE}
                    onValueChange={(value) =>
                        changeFilters({ segment: value === ALL_OPTION_VALUE ? null : value })
                    }
                >
                    <SelectTrigger className="w-40" aria-label="Segment">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL_OPTION_VALUE}>All segments</SelectItem>
                        {(profile?.segments ?? []).map(renderSegment)}
                    </SelectContent>
                </Select>

                <Select
                    value={state.location ? String(state.location) : ALL_OPTION_VALUE}
                    onValueChange={(value) =>
                        changeFilters({ location: value === ALL_OPTION_VALUE ? null : Number(value) })
                    }
                >
                    <SelectTrigger className="w-48" aria-label="Location">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="max-h-80">
                        <SelectItem value={ALL_OPTION_VALUE}>All locations</SelectItem>
                        {provinces.map(renderProvince)}
                    </SelectContent>
                </Select>

                <Select
                    value={state.status ?? ALL_OPTION_VALUE}
                    onValueChange={(value) =>
                        changeFilters({
                            status: value === ALL_OPTION_VALUE ? null : (value as typeof state.status),
                        })
                    }
                >
                    <SelectTrigger className="w-40" aria-label="Status">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL_OPTION_VALUE}>Any status</SelectItem>
                        {LEAD_STATUS_OPTIONS.map(renderStatusOption)}
                    </SelectContent>
                </Select>

                <Select
                    value={state.assignee ?? ALL_OPTION_VALUE}
                    onValueChange={(value) =>
                        changeFilters({ assignee: value === ALL_OPTION_VALUE ? null : value })
                    }
                >
                    <SelectTrigger className="w-44" aria-label="Assigned to">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL_OPTION_VALUE}>Anyone</SelectItem>
                        <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
                        {assignees.map(renderUser)}
                    </SelectContent>
                </Select>

                {(sources.length > 1 || state.source) && (
                    <Select
                        value={state.source ?? ALL_OPTION_VALUE}
                        onValueChange={(value) => changeFilters({ source: value === ALL_OPTION_VALUE ? null : value })}
                    >
                        <SelectTrigger className="w-52" aria-label="Found by">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value={ALL_OPTION_VALUE}>Found by anyone</SelectItem>
                            {state.source && !sources.some((source) => source.key === state.source) && (
                                <SelectItem value={state.source}>{getSourceLabel(state.source)}</SelectItem>
                            )}
                            {sources.map(renderSource)}
                        </SelectContent>
                    </Select>
                )}

                <Popover>
                    <PopoverTrigger asChild>
                        <Button variant="outline">
                            <SlidersHorizontal />
                            Contact details
                            {moreFilterCount > 0 && (
                                <span className="ml-1 rounded-full bg-primary px-1.5 text-xs text-primary-foreground">
                                    {moreFilterCount}
                                </span>
                            )}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent align="start" className="w-72 space-y-4">
                        <p className="text-sm font-medium">Only leads that have…</p>
                        {FILTER_FLAGS.map(renderFlag)}
                        <div className="space-y-2">
                            <Label>Score</Label>
                            <Select
                                value={state.minScore ? String(state.minScore) : ALL_OPTION_VALUE}
                                onValueChange={(value) =>
                                    changeFilters({ minScore: value === ALL_OPTION_VALUE ? null : Number(value) })
                                }
                            >
                                <SelectTrigger className="w-full" aria-label="Minimum score">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={ALL_OPTION_VALUE}>Any score</SelectItem>
                                    {MIN_SCORES.map(renderMinScoreOption)}
                                </SelectContent>
                            </Select>
                        </div>
                    </PopoverContent>
                </Popover>

                {activeFilterCount > 0 && (
                    <Button variant="ghost" onClick={clearFilters}>
                        <X />
                        Clear filters
                    </Button>
                )}
            </div>
        </div>
    );
};

export default LeadsFilters;
