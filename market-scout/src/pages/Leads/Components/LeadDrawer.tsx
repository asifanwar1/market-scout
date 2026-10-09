import {
    Ban,
    ExternalLink,
    Globe,
    Mail,
    MapPin,
    MessageCircle,
    Phone,
    Save,
    Star,
} from "lucide-react";
import { useState } from "react";

import type { TBusinessDetail, TContactPoint } from "@/api/services/businesses/businesses.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import CopyButton from "@/components/custom/CopyButton";
import Loading from "@/components/custom/Loading";
import ScoreBadge from "@/components/custom/ScoreBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { LEAD_STATUS_OPTIONS } from "@/constants";
import type { LeadStatus } from "@/constants/lead-status.constants";
import { useGetAssignees, useGetBusiness, useMarkDoNotContact, useUpdateBusiness } from "@/hooks/api/businesses.queries";
import { useGetPipelineConfig } from "@/hooks/api/pipeline.queries";
import type { TUpdateBusinessBody } from "@/api/services/businesses/businesses.request.types";
import type { TOutcomeInput } from "@/api/services/pipeline/pipeline.request.types";
import type { ClosingStatus } from "@/constants/pipeline.constants";
import { isClosingStatus } from "@/utils/pipeline.utils";
import LeadTasks from "./LeadTasks";
import LeadTimeline from "./LeadTimeline";
import OutcomeDialog from "./OutcomeDialog";
import OutcomeSummary from "./OutcomeSummary";
import { showToast } from "@/lib/toast";
import { formatDate, formatDateTime, formatPhone, getSourceLabel, whatsappLink } from "@/utils/format.utils";
import { NOTES_MAX_LENGTH, REASON_MAX_LENGTH } from "@/constants/limits.constants";
import { CONTACT_KIND } from "@/constants/source.constants";

const NOT_ASSIGNED = "none";

type TLeadDrawerProps = {
    leadId: number | null;
    onClose: () => void;
};

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <section className="space-y-3 border-b px-6 py-5 last:border-b-0">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
        {children}
    </section>
);

const LeadDrawer = ({ leadId, onClose }: TLeadDrawerProps) => {
    const { data: lead, isPending, isError } = useGetBusiness(leadId);

    return (
        <Sheet open={leadId !== null} onOpenChange={(open) => !open && onClose()}>
            <SheetContent className="w-full gap-0 overflow-y-auto p-0 sm:max-w-lg">
                {isPending || isError || !lead ? (
                    <>
                        <SheetHeader className="sr-only">
                            <SheetTitle>Lead details</SheetTitle>
                            <SheetDescription>Loading the lead</SheetDescription>
                        </SheetHeader>
                        {isError ? (
                            <p className="p-6 text-sm text-muted-foreground">
                                This lead isn't available any more. It may have been removed or
                                marked do not contact.
                            </p>
                        ) : (
                            <Loading />
                        )}
                    </>
                ) : (
                    <LeadDetails key={lead.id} lead={lead} onClose={onClose} />
                )}
            </SheetContent>
        </Sheet>
    );
};

const ContactRow = ({ contact }: { contact: TContactPoint }) => {
    const isPhone = contact.kind === CONTACT_KIND.PHONE || contact.kind === CONTACT_KIND.WHATSAPP;
    const display = isPhone ? formatPhone(contact.value) : contact.value;

    return (
        <li className="flex items-center gap-2">
            <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium tabular-nums">{display}</p>
                <p className="text-xs text-muted-foreground">
                    {contact.kind === CONTACT_KIND.PHONE && (contact.is_mobile ? "Mobile" : "Landline")}
                    {contact.kind === CONTACT_KIND.WHATSAPP && "WhatsApp"}
                    {contact.kind === CONTACT_KIND.EMAIL && "Email"}
                    {(contact.kind === CONTACT_KIND.FACEBOOK || contact.kind === CONTACT_KIND.INSTAGRAM) && contact.kind}
                    {" · "}via {getSourceLabel(contact.source_key)}
                </p>
            </div>
            {contact.whatsapp_likely && (
                <Badge variant="secondary" className="bg-success text-success-foreground">
                    WhatsApp
                </Badge>
            )}
            {isPhone && (
                <>
                    <Button asChild variant="ghost" size="icon-xs" aria-label={`Call ${display}`}>
                        <a href={`tel:${contact.value}`}>
                            <Phone />
                        </a>
                    </Button>
                    {contact.whatsapp_likely && (
                        <Button asChild variant="ghost" size="icon-xs" aria-label={`WhatsApp ${display}`}>
                            <a href={whatsappLink(contact.value)} target="_blank" rel="noopener noreferrer">
                                <MessageCircle />
                            </a>
                        </Button>
                    )}
                </>
            )}
            {contact.kind === CONTACT_KIND.EMAIL && (
                <Button asChild variant="ghost" size="icon-xs" aria-label={`Email ${contact.value}`}>
                    <a href={`mailto:${contact.value}`}>
                        <Mail />
                    </a>
                </Button>
            )}
            {(contact.kind === CONTACT_KIND.FACEBOOK || contact.kind === CONTACT_KIND.INSTAGRAM) && (
                <Button asChild variant="ghost" size="icon-xs" aria-label={`Open ${contact.kind}`}>
                    <a href={contact.value} target="_blank" rel="noopener noreferrer">
                        <ExternalLink />
                    </a>
                </Button>
            )}
            <CopyButton value={contact.value} label={display} />
        </li>
    );
};

const LeadDetails = ({ lead, onClose }: { lead: TBusinessDetail; onClose: () => void }) => {
    const { mutateAsync: updateLead, isPending: isSaving } = useUpdateBusiness();
    const { mutateAsync: markDoNotContact, isPending: isBlocking } = useMarkDoNotContact();
    const { data: assignees = [] } = useGetAssignees();
    const currency = useGetPipelineConfig();

    const [notes, setNotes] = useState(lead.notes ?? "");
    const [showBlock, setShowBlock] = useState(false);
    const [blockReason, setBlockReason] = useState("");
    const [pendingStatus, setPendingStatus] = useState<ClosingStatus | null>(null);
    const [isEditingOutcome, setIsEditingOutcome] = useState(false);

    const notesChanged = notes.trim() !== (lead.notes ?? "");
    const topClassification = lead.classifications[0];
    const contacts = [...lead.contacts].sort((a, b) => a.kind.localeCompare(b.kind) || a.id - b.id);

    const currentClosingStatus = isClosingStatus(lead.lead_status) ? lead.lead_status : null;
    const dialogStatus = pendingStatus ?? (isEditingOutcome ? currentClosingStatus : null);
    const canSkipOutcome = pendingStatus !== null;

    const save = async (body: TUpdateBusinessBody, message: string) => {
        await updateLead({ id: lead.id, body });
        showToast.success(message);
    };

    const onStatusChange = (value: string) => {
        if (isClosingStatus(value)) {
            setPendingStatus(value);
            return;
        }
        void save({ lead_status: value as LeadStatus }, "Status updated");
    };

    const closeOutcomeDialog = () => {
        setPendingStatus(null);
        setIsEditingOutcome(false);
    };

    const saveOutcome = async (outcome: TOutcomeInput) => {
        const body: TUpdateBusinessBody = pendingStatus ? { lead_status: pendingStatus, outcome } : { outcome };
        await save(body, pendingStatus ? "Status updated" : "Deal details saved");
        closeOutcomeDialog();
    };

    const skipOutcome = async () => {
        if (pendingStatus) await save({ lead_status: pendingStatus }, "Status updated");
        closeOutcomeDialog();
    };

    const startEditingOutcome = () => {
        setIsEditingOutcome(true);
    };

    const handleBlock = async () => {
        await markDoNotContact({ id: lead.id, body: { reason: blockReason.trim() || null } });
        showToast.success(`${lead.name} is now on the do-not-contact list`);
        setShowBlock(false);
        onClose();
    };

    const renderSource = (source: (typeof lead.sources)[number]) => (
        <li key={`${source.source_key}-${source.external_id}`} className="flex justify-between gap-2">
            <span>{getSourceLabel(source.source_key)}</span>
            <span className="text-muted-foreground">{formatDateTime(source.fetched_at)}</span>
        </li>
    );
    const renderCategory = (category: (typeof lead.categories)[number]) => (
        <Badge key={category} variant="secondary" className="font-normal">
            {category}
        </Badge>
    );
    const renderContact = (contact: (typeof contacts)[number]) => (
        <ContactRow key={contact.id} contact={contact} />
    );
    const renderUser = (user: (typeof assignees)[number]) => (
        <SelectItem key={user.id} value={String(user.id)}>
            {user.full_name}
        </SelectItem>
    );
    const renderStatusOption = (option: (typeof LEAD_STATUS_OPTIONS)[number]) => (
        <SelectItem key={option.value} value={option.value}>
            {option.label}
        </SelectItem>
    );
    return (
        <>
            <SheetHeader className="space-y-1 border-b px-6 py-5 pr-12">
                <div className="flex items-start justify-between gap-3">
                    <SheetTitle className="text-lg leading-snug">{lead.name}</SheetTitle>
                    <ScoreBadge score={topClassification?.score} />
                </div>
                <SheetDescription className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    {topClassification?.segment_name && (
                        <Badge variant="outline">{topClassification.segment_name}</Badge>
                    )}
                    <span>{[lead.city, lead.province].filter(Boolean).join(", ") || "Unknown location"}</span>
                </SheetDescription>
            </SheetHeader>

            <Section title="Sales">
                <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                        <Label htmlFor="lead-status">Status</Label>
                        <Select
                            value={lead.lead_status}
                            disabled={isSaving}
                            onValueChange={onStatusChange}
                        >
                            <SelectTrigger id="lead-status" className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {LEAD_STATUS_OPTIONS.map(renderStatusOption)}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="lead-assignee">Assigned to</Label>
                        <Select
                            value={lead.assigned_to ? String(lead.assigned_to.id) : NOT_ASSIGNED}
                            disabled={isSaving}
                            onValueChange={(value) =>
                                save(
                                    { assigned_to_id: value === NOT_ASSIGNED ? null : Number(value) },
                                    value === NOT_ASSIGNED ? "Unassigned" : "Assigned",
                                )
                            }
                        >
                            <SelectTrigger id="lead-assignee" className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={NOT_ASSIGNED}>Unassigned</SelectItem>
                                {assignees.map(renderUser)}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
                {lead.outcome && <OutcomeSummary outcome={lead.outcome} currency={currency} onEdit={startEditingOutcome} />}
                <div className="space-y-1.5">
                    <Label htmlFor="lead-notes">Notes</Label>
                    <Textarea
                        id="lead-notes"
                        rows={4}
                        maxLength={NOTES_MAX_LENGTH}
                        value={notes}
                        placeholder="Who you spoke to, what they need, when to follow up…"
                        onChange={(event) => setNotes(event.target.value)}
                    />
                    <div className="flex justify-end">
                        <Button
                            size="sm"
                            disabled={!notesChanged || isSaving}
                            onClick={() => save({ notes: notes.trim() || null }, "Notes saved")}
                        >
                            <Save />
                            Save notes
                        </Button>
                    </div>
                </div>
            </Section>

            <Section title="Follow-ups">
                <LeadTasks businessId={lead.id} />
            </Section>

            <Section title="History">
                <LeadTimeline businessId={lead.id} />
            </Section>

            <Section title="Contact">
                {contacts.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                        No phone or email found yet. A run with website enrichment may find some.
                    </p>
                ) : (
                    <ul className="space-y-3">
                        {contacts.map(renderContact)}
                    </ul>
                )}
                {lead.website && (
                    <a
                        href={lead.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-sm text-primary hover:underline"
                    >
                        <Globe className="size-4" />
                        {lead.website.replace(/^https?:\/\//, "")}
                    </a>
                )}
            </Section>

            <Section title="Details">
                <dl className="space-y-2 text-sm">
                    {lead.address && (
                        <div className="flex gap-2">
                            <MapPin className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                            <div>
                                <dd>{lead.address}</dd>
                                {lead.latitude !== null && lead.longitude !== null && (
                                    <a
                                        href={`https://www.google.com/maps?q=${lead.latitude},${lead.longitude}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs text-primary hover:underline"
                                    >
                                        Open in Maps
                                    </a>
                                )}
                            </div>
                        </div>
                    )}
                    {lead.rating !== null && (
                        <div className="flex items-center gap-2">
                            <Star className="size-4 text-muted-foreground" />
                            <dd>
                                {lead.rating.toFixed(1)}
                                {lead.review_count !== null && (
                                    <span className="text-muted-foreground"> · {lead.review_count} reviews</span>
                                )}
                            </dd>
                        </div>
                    )}
                    {lead.categories.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                            {lead.categories.map(renderCategory)}
                        </div>
                    )}
                </dl>
            </Section>

            <Section title="Where this came from">
                <ul className="space-y-1.5 text-sm">
                    {lead.sources.map(renderSource)}
                </ul>
                <p className="text-xs text-muted-foreground">
                    First found {formatDate(lead.first_seen_at)} · last seen {formatDate(lead.last_seen_at)}
                    {lead.enriched_at && ` · website read ${formatDate(lead.enriched_at)}`}
                </p>
            </Section>

            <Section title="Privacy">
                <p className="text-sm text-muted-foreground">
                    If this business asks not to be contacted, record it. They'll be removed from
                    every list and won't be added again by future runs.
                </p>
                <Button variant="destructive" size="sm" onClick={() => setShowBlock(true)}>
                    <Ban />
                    Mark do not contact
                </Button>
            </Section>

            <OutcomeDialog
                status={dialogStatus}
                leadName={lead.name}
                currency={currency}
                initial={pendingStatus ? null : lead.outcome}
                isSaving={isSaving}
                canSkip={canSkipOutcome}
                onSave={saveOutcome}
                onSkip={skipOutcome}
                onClose={closeOutcomeDialog}
            />

            <ConfirmationModal
                open={showBlock}
                destructive
                title="Mark as do not contact?"
                description={`${lead.name} and its phone numbers and emails will be hidden from all leads and skipped by future runs. Only an admin can undo this.`}
                confirmText="Mark do not contact"
                isLoading={isBlocking}
                onConfirm={handleBlock}
                onClose={() => setShowBlock(false)}
            >
                <div className="space-y-1.5">
                    <Label htmlFor="block-reason">Reason (optional)</Label>
                    <Textarea
                        id="block-reason"
                        rows={2}
                        maxLength={REASON_MAX_LENGTH}
                        value={blockReason}
                        placeholder="e.g. Owner asked us to stop calling"
                        onChange={(event) => setBlockReason(event.target.value)}
                    />
                </div>
            </ConfirmationModal>
        </>
    );
};

export default LeadDrawer;
