import { ChevronDown, Download, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CRM_EXPORT_HEADING, CRM_EXPORT_OPTIONS, EXPORT_BUTTON_LABEL, EXPORT_OPTIONS } from "../Leads.constants";
import type { TLeadsPage } from "../Leads.Container";

type TExportMenuProps = {
    page: TLeadsPage;
};

const ExportMenu = ({ page }: TExportMenuProps) => {
    const { exportLeads, exportCrm, isExporting, isExportDisabled } = page;

    const renderOption = (option: (typeof EXPORT_OPTIONS)[number]) => (
        <DropdownMenuItem key={option.format} onSelect={() => void exportLeads(option.format)}>
            {option.label}
        </DropdownMenuItem>
    );

    const renderCrmOption = (option: (typeof CRM_EXPORT_OPTIONS)[number]) => (
        <DropdownMenuItem key={option.layout} onSelect={() => void exportCrm(option.layout)}>
            {option.label}
        </DropdownMenuItem>
    );

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="outline" disabled={isExportDisabled}>
                    {isExporting ? <Loader2 className="animate-spin" /> : <Download />}
                    {EXPORT_BUTTON_LABEL}
                    <ChevronDown />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-40">
                {EXPORT_OPTIONS.map(renderOption)}
                <DropdownMenuSeparator />
                <DropdownMenuLabel>{CRM_EXPORT_HEADING}</DropdownMenuLabel>
                {CRM_EXPORT_OPTIONS.map(renderCrmOption)}
            </DropdownMenuContent>
        </DropdownMenu>
    );
};

export default ExportMenu;
