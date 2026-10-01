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
import { LEAD_STATUS_OPTIONS } from "@/constants";
import { getSourceLabel } from "@/utils/format.utils";
import { useStore } from "@/store";
import { ALL, UNASSIGNED, type TLeadsPage } from "./Leads.Container";

const MIN_SCORES = [
    { value: "40", label: "40+ (some contact detail)" },
    { value: "70", label: "70+ (ready to call)" },
];

type TLeadsFiltersProps = {
    page: TLeadsPage;
};

const LeadsFilters = ({ page }: TLeadsFiltersProps) => {
    const {
        state,
        searchInput,
        setSearchInput,
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

    // Country -> provinces -> cities; picking a province means every city inside it.
    const provinces = geographyTree.flatMap((country) => country.children);

    return (
        <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-56 flex-1 sm:max-w-xs">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        value={searchInput}
                        onChange={(event) => setSearchInput(event.target.value)}
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
                            {profiles.map((item) => (
                                <SelectItem key={item.id} value={String(item.id)}>
                                    {item.name}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                )}

                <Select
                    value={state.segment ?? ALL}
                    onValueChange={(value) =>
                        changeFilters({ segment: value === ALL ? null : value })
                    }
                >
                    <SelectTrigger className="w-40" aria-label="Segment">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL}>All segments</SelectItem>
                        {(profile?.segments ?? []).map((segment) => (
                            <SelectItem key={segment.id} value={segment.slug}>
                                {segment.name}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Select
                    value={state.location ? String(state.location) : ALL}
                    onValueChange={(value) =>
                        changeFilters({ location: value === ALL ? null : Number(value) })
                    }
                >
                    <SelectTrigger className="w-48" aria-label="Location">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="max-h-80">
                        <SelectItem value={ALL}>All locations</SelectItem>
                        {provinces.map((province) => (
                            <SelectGroup key={province.id}>
                                <SelectSeparator />
                                <SelectLabel>{province.name}</SelectLabel>
                                <SelectItem value={String(province.id)}>
                                    All of {province.name}
                                </SelectItem>
                                {province.children.map((city) => (
                                    <SelectItem key={city.id} value={String(city.id)}>
                                        {city.name}
                                    </SelectItem>
                                ))}
                            </SelectGroup>
                        ))}
                    </SelectContent>
                </Select>

                <Select
                    value={state.status ?? ALL}
                    onValueChange={(value) =>
                        changeFilters({
                            status: value === ALL ? null : (value as typeof state.status),
                        })
                    }
                >
                    <SelectTrigger className="w-40" aria-label="Status">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL}>Any status</SelectItem>
                        {LEAD_STATUS_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                                {option.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Select
                    value={state.assignee ?? ALL}
                    onValueChange={(value) =>
                        changeFilters({ assignee: value === ALL ? null : value })
                    }
                >
                    <SelectTrigger className="w-44" aria-label="Assigned to">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ALL}>Anyone</SelectItem>
                        <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
                        {assignees.map((user) => (
                            <SelectItem key={user.id} value={String(user.id)}>
                                {user.full_name}
                                {user.id === currentUserId ? " (me)" : ""}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                {(sources.length > 1 || state.source) && (
                    <Select
                        value={state.source ?? ALL}
                        onValueChange={(value) => changeFilters({ source: value === ALL ? null : value })}
                    >
                        <SelectTrigger className="w-52" aria-label="Found by">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value={ALL}>Found by anyone</SelectItem>
                            {state.source && !sources.some((source) => source.key === state.source) && (
                                <SelectItem value={state.source}>{getSourceLabel(state.source)}</SelectItem>
                            )}
                            {sources.map((source) => (
                                <SelectItem key={source.key} value={source.key}>
                                    {source.name}
                                </SelectItem>
                            ))}
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
                        {(
                            [
                                ["phone", "A phone number"],
                                ["whatsapp", "A WhatsApp-capable number"],
                                ["email", "An email address"],
                                ["website", "A website"],
                            ] as const
                        ).map(([key, label]) => (
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
                        ))}
                        <div className="space-y-2">
                            <Label>Score</Label>
                            <Select
                                value={state.minScore ? String(state.minScore) : ALL}
                                onValueChange={(value) =>
                                    changeFilters({ minScore: value === ALL ? null : Number(value) })
                                }
                            >
                                <SelectTrigger className="w-full" aria-label="Minimum score">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={ALL}>Any score</SelectItem>
                                    {MIN_SCORES.map((option) => (
                                        <SelectItem key={option.value} value={option.value}>
                                            {option.label}
                                        </SelectItem>
                                    ))}
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
