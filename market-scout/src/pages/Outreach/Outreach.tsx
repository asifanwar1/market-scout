import { Send } from "lucide-react";

import type { TOutreachMessage } from "@/api/services/outreach/outreach.response.types";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import Pagination from "@/components/custom/Pagination";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ALL_OPTION_VALUE } from "@/constants";
import MessageRow from "./Components/MessageRow";
import TemplatesCard from "./Components/TemplatesCard";
import {
    LOG_DESCRIPTION,
    LOG_EMPTY_DESCRIPTION,
    LOG_EMPTY_TITLE,
    LOG_TITLE,
    OUTREACH_PAGE_DESCRIPTION,
    OUTREACH_PAGE_TITLE,
} from "./Outreach.constants";
import { useOutreachPage } from "./Outreach.Container";

const Outreach = () => {
    const {
        messages,
        total,
        hasMessages,
        mineOnly,
        statusValue,
        statusOptions,
        page,
        pageSize,
        isPending,
        isAdmin,
        onMineChange,
        onStatusChange,
        onPageChange,
        onPageSizeChange,
    } = useOutreachPage();

    const renderMessage = (message: TOutreachMessage) => <MessageRow key={message.id} message={message} />;

    const renderStatus = (option: (typeof statusOptions)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );

    return (
        <div className="space-y-6">
            <PageHeader title={OUTREACH_PAGE_TITLE} description={OUTREACH_PAGE_DESCRIPTION} />

            <TemplatesCard isAdmin={isAdmin} />

            <Card>
                <CardHeader>
                    <CardTitle>{LOG_TITLE}</CardTitle>
                    <CardDescription>{LOG_DESCRIPTION}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex flex-wrap items-center gap-4">
                        <Select value={statusValue} onValueChange={onStatusChange}>
                            <SelectTrigger className="w-56" aria-label="Filter by status">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={ALL_OPTION_VALUE}>All messages</SelectItem>
                                {statusOptions.map(renderStatus)}
                            </SelectContent>
                        </Select>
                        <div className="flex items-center gap-2">
                            <Switch id="outreach-mine" checked={mineOnly} onCheckedChange={onMineChange} />
                            <Label htmlFor="outreach-mine" className="text-sm font-normal">
                                Only mine
                            </Label>
                        </div>
                    </div>

                    {isPending ? (
                        <Loading />
                    ) : hasMessages ? (
                        <ul className="divide-y rounded-md border">{messages.map(renderMessage)}</ul>
                    ) : (
                        <EmptyState icon={Send} title={LOG_EMPTY_TITLE} description={LOG_EMPTY_DESCRIPTION} />
                    )}

                    {hasMessages && (
                        <Pagination
                            page={page}
                            pageSize={pageSize}
                            total={total}
                            onPageChange={onPageChange}
                            onPageSizeChange={onPageSizeChange}
                        />
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default Outreach;
