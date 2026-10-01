import type { TColumnMapping } from "@/api/services/imports/imports.request.types";
import type { TImportPreview } from "@/api/services/imports/imports.response.types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toggleColumn } from "./importForm";

type TColumnsStepProps = {
    preview: TImportPreview;
    mapping: TColumnMapping;
    onChange: (mapping: TColumnMapping) => void;
};

const NONE = "__none__";

type TSingleField = "name" | "website" | "address" | "city" | "latitude" | "longitude" | "category";

const SINGLE_FIELDS: { field: TSingleField; label: string; hint?: string; required?: boolean }[] = [
    { field: "name", label: "Business name", required: true },
    { field: "website", label: "Website" },
    { field: "address", label: "Address", hint: "Also used to find the city when there is no city column" },
    { field: "city", label: "City" },
    { field: "latitude", label: "Latitude", hint: "Optional; places the business on the map" },
    { field: "longitude", label: "Longitude" },
    { field: "category", label: "Category or type", hint: "Optional; kept with the lead" },
];

const ColumnChecks = ({
    label,
    hint,
    columns,
    selected,
    onToggle,
}: {
    label: string;
    hint: string;
    columns: string[];
    selected: string[];
    onToggle: (column: string, on: boolean) => void;
}) => (
    <fieldset className="space-y-2">
        <legend className="text-sm font-medium">{label}</legend>
        <p className="text-xs text-muted-foreground">{hint}</p>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
            {columns.map((column) => {
                const id = `${label}-${column}`;
                return (
                    <div key={column} className="flex items-center gap-2">
                        <Checkbox id={id} checked={selected.includes(column)} onCheckedChange={(checked) => onToggle(column, checked === true)} />
                        <Label htmlFor={id} className="font-normal">
                            {column}
                        </Label>
                    </div>
                );
            })}
        </div>
    </fieldset>
);

const ColumnsStep = ({ preview, mapping, onChange }: TColumnsStepProps) => {
    return (
        <Card>
            <CardHeader>
                <CardTitle>2 · What each column is</CardTitle>
                <CardDescription>We guessed from the headers. Check them against the sample below and fix anything that is off.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2">
                    {SINGLE_FIELDS.map(({ field, label, hint, required }) => (
                        <div key={field} className="space-y-1.5">
                            <Label htmlFor={`map-${field}`}>
                                {label}
                                {required && <span className="text-destructive"> *</span>}
                            </Label>
                            <Select
                                value={mapping[field] || NONE}
                                onValueChange={(value) => onChange({ ...mapping, [field]: value === NONE ? (field === "name" ? "" : null) : value })}
                            >
                                <SelectTrigger id={`map-${field}`} className="w-full">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={NONE}>{required ? "Choose a column" : "Not in the file"}</SelectItem>
                                    {preview.columns.map((column) => (
                                        <SelectItem key={column} value={column}>
                                            {column}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
                        </div>
                    ))}
                </div>

                <div className="space-y-5 border-t pt-5">
                    <ColumnChecks
                        label="Phone numbers"
                        hint="Tick every column that holds a phone or mobile number. A cell may hold several."
                        columns={preview.columns}
                        selected={mapping.phones}
                        onToggle={(column, on) => onChange({ ...mapping, phones: toggleColumn(mapping.phones, column, on) })}
                    />
                    <ColumnChecks
                        label="Email addresses"
                        hint="Tick every column that holds an email address."
                        columns={preview.columns}
                        selected={mapping.emails}
                        onToggle={(column, on) => onChange({ ...mapping, emails: toggleColumn(mapping.emails, column, on) })}
                    />
                </div>

                <div className="space-y-2 border-t pt-5">
                    <p className="text-sm font-medium">The first rows of your file</p>
                    <div className="overflow-x-auto rounded-lg border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    {preview.columns.map((column) => (
                                        <TableHead key={column} className="whitespace-nowrap">
                                            {column}
                                        </TableHead>
                                    ))}
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {preview.sample.map((row, index) => (
                                    <TableRow key={index}>
                                        {preview.columns.map((column) => (
                                            <TableCell key={column} className="max-w-56 truncate">
                                                {row[column]}
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export default ColumnsStep;
