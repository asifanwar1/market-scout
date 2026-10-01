import type { TColumnMapping } from "@/api/services/imports/imports.request.types";
import type { TImportPreview } from "@/api/services/imports/imports.response.types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toggleColumn } from "../importForm";
import { NAME_FIELD, NO_COLUMN_VALUE, SINGLE_FIELDS, type TSingleFieldConfig } from "../NewImport.constants";

type TColumnsStepProps = {
    preview: TImportPreview;
    mapping: TColumnMapping;
    onChange: (mapping: TColumnMapping) => void;
};

type TColumnChecksProps = {
    label: string;
    hint: string;
    columns: string[];
    selected: string[];
    onToggle: (column: string, on: boolean) => void;
};

const ColumnChecks = ({ label, hint, columns, selected, onToggle }: TColumnChecksProps) => {
    const renderColumn = (column: string) => {
        const id = `${label}-${column}`;
        return (
            <div key={column} className="flex items-center gap-2">
                <Checkbox id={id} checked={selected.includes(column)} onCheckedChange={(checked) => onToggle(column, checked === true)} />
                <Label htmlFor={id} className="font-normal">
                    {column}
                </Label>
            </div>
        );
    };

    return (
        <fieldset className="space-y-2">
            <legend className="text-sm font-medium">{label}</legend>
            <p className="text-xs text-muted-foreground">{hint}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-2">{columns.map(renderColumn)}</div>
        </fieldset>
    );
};

const ColumnsStep = ({ preview, mapping, onChange }: TColumnsStepProps) => {
    const renderColumnOption = (column: string) => (
        <SelectItem key={column} value={column}>
            {column}
        </SelectItem>
    );

    const renderHeader = (column: string) => (
        <TableHead key={column} className="whitespace-nowrap">
            {column}
        </TableHead>
    );

    const renderRow = (row: Record<string, string>, index: number) => {
        const renderCell = (column: string) => (
            <TableCell key={column} className="max-w-56 truncate">
                {row[column]}
            </TableCell>
        );

        return <TableRow key={index}>{preview.columns.map(renderCell)}</TableRow>;
    };

    const renderField = ({ field, label, hint, required }: TSingleFieldConfig) => {
        const onValueChange = (value: string) => {
            const emptyValue = field === NAME_FIELD ? "" : null;
            onChange({ ...mapping, [field]: value === NO_COLUMN_VALUE ? emptyValue : value });
        };

        return (
            <div key={field} className="space-y-1.5">
                <Label htmlFor={`map-${field}`}>
                    {label}
                    {required && <span className="text-destructive"> *</span>}
                </Label>
                <Select value={mapping[field] || NO_COLUMN_VALUE} onValueChange={onValueChange}>
                    <SelectTrigger id={`map-${field}`} className="w-full">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value={NO_COLUMN_VALUE}>{required ? "Choose a column" : "Not in the file"}</SelectItem>
                        {preview.columns.map(renderColumnOption)}
                    </SelectContent>
                </Select>
                {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
            </div>
        );
    };

    const togglePhone = (column: string, on: boolean) => {
        onChange({ ...mapping, phones: toggleColumn(mapping.phones, column, on) });
    };

    const toggleEmail = (column: string, on: boolean) => {
        onChange({ ...mapping, emails: toggleColumn(mapping.emails, column, on) });
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>2 · What each column is</CardTitle>
                <CardDescription>We guessed from the headers. Check them against the sample below and fix anything that is off.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2">{SINGLE_FIELDS.map(renderField)}</div>

                <div className="space-y-5 border-t pt-5">
                    <ColumnChecks
                        label="Phone numbers"
                        hint="Tick every column that holds a phone or mobile number. A cell may hold several."
                        columns={preview.columns}
                        selected={mapping.phones}
                        onToggle={togglePhone}
                    />
                    <ColumnChecks
                        label="Email addresses"
                        hint="Tick every column that holds an email address."
                        columns={preview.columns}
                        selected={mapping.emails}
                        onToggle={toggleEmail}
                    />
                </div>

                <div className="space-y-2 border-t pt-5">
                    <p className="text-sm font-medium">The first rows of your file</p>
                    <div className="overflow-x-auto rounded-lg border">
                        <Table>
                            <TableHeader>
                                <TableRow>{preview.columns.map(renderHeader)}</TableRow>
                            </TableHeader>
                            <TableBody>{preview.sample.map(renderRow)}</TableBody>
                        </Table>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export default ColumnsStep;
