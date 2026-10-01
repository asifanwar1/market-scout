import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import type { TNewImport } from "../NewImport.Container";
import { LIST_LABEL_MAX_LENGTH } from "@/constants/limits.constants";

type TSettingsStepProps = {
    page: TNewImport;
};

const NONE = "__none__";

const SettingsStep = ({ page }: TSettingsStepProps) => {
    const provinces = page.geographyTree.flatMap((country) => country.children);

    const renderSegment = (segment: (typeof page.segments)[number]) => (
        <SelectItem key={segment.id} value={segment.slug}>
            Every row is: {segment.name}
        </SelectItem>
    );
    const renderProfile = (profile: (typeof page.profiles)[number]) => (
        <SelectItem key={profile.id} value={String(profile.id)}>
            {profile.name}
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
                {province.children.map(renderCity)}
            </SelectGroup>
        );
    };
    return (
        <Card>
            <CardHeader>
                <CardTitle>3 · About this list</CardTitle>
                <CardDescription>This is how the leads are named, scored and filed.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
                <div className="space-y-1.5">
                    <Label htmlFor="import-label">Name of the list</Label>
                    <Input
                        id="import-label"
                        value={page.label}
                        maxLength={LIST_LABEL_MAX_LENGTH}
                        onChange={(event) => page.setLabel(event.target.value)}
                        placeholder="e.g. AEDB certified installers 2026"
                        className="sm:max-w-md"
                    />
                    <p className="text-xs text-muted-foreground">
                        Leads show it as where they were found. Importing a newer version under the same name updates the same list instead of making a new one.
                    </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                    {page.profiles.length > 1 && (
                        <div className="space-y-1.5">
                            <Label htmlFor="import-profile">Profile</Label>
                            <Select value={page.profileId ? String(page.profileId) : ""} onValueChange={(value) => page.setProfileId(Number(value))}>
                                <SelectTrigger id="import-profile" className="w-full">
                                    <SelectValue placeholder="Choose a profile" />
                                </SelectTrigger>
                                <SelectContent>
                                    {page.profiles.map(renderProfile)}
                                </SelectContent>
                            </Select>
                        </div>
                    )}

                    <div className="space-y-1.5">
                        <Label htmlFor="import-segment">Kind of business</Label>
                        <Select value={page.segmentSlug ?? NONE} onValueChange={(value) => page.setSegmentSlug(value === NONE ? null : value)}>
                            <SelectTrigger id="import-segment" className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={NONE}>Decide from each business's name</SelectItem>
                                {page.segments.map(renderSegment)}
                            </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">A certified-installer list is all installers; a chamber directory is mixed, so let the name decide.</p>
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="import-city">City when the file doesn't say</Label>
                        <Select value={page.cityId ? String(page.cityId) : NONE} onValueChange={(value) => page.setCityId(value === NONE ? null : Number(value))}>
                            <SelectTrigger id="import-city" className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={NONE}>Leave those without a city</SelectItem>
                                {provinces.map(renderProvince)}
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <div className="flex items-start gap-2 border-t pt-5">
                    <Checkbox
                        id="import-lookup"
                        disabled={!page.canLookUp}
                        checked={page.lookupContacts}
                        onCheckedChange={(checked) => page.setLookupContacts(checked === true)}
                    />
                    <div className="space-y-0.5">
                        <Label htmlFor="import-lookup" className={page.canLookUp ? undefined : "text-muted-foreground"}>
                            Look up missing phones in Overture Maps
                        </Label>
                        <p className="text-xs text-muted-foreground">
                            {page.canLookUp
                                ? "For rows with no phone: if exactly one business in Overture Maps has the same name in the same city, its phone, email and website are used. Anything less certain is left alone."
                                : "Needs the Overture Maps data. Download it first (see the Sources screen)."}
                        </p>
                    </div>
                </div>

                <div className="flex items-start gap-2">
                    <Checkbox id="import-require-contact" checked={page.requireContact} onCheckedChange={(checked) => page.setRequireContact(checked === true)} />
                    <div className="space-y-0.5">
                        <Label htmlFor="import-require-contact">Skip rows with no contact details</Label>
                        <p className="text-xs text-muted-foreground">A business with no phone, email or website can't be contacted. Untick this to keep them anyway.</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export default SettingsStep;
