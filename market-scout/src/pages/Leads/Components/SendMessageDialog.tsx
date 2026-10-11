import { Check, Copy, ExternalLink, Loader2, TriangleAlert } from "lucide-react";
import { useState } from "react";

import type { TBusinessDetail, TContactPoint } from "@/api/services/businesses/businesses.response.types";
import type { TPreparedMessage } from "@/api/services/outreach/outreach.response.types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { CONTACT_KIND } from "@/constants/source.constants";
import {
    MESSAGE_CHANNEL_LABELS,
    MESSAGE_STATUS,
    OUTREACH_CHANNEL,
    type OutreachChannel,
} from "@/constants/outreach.constants";
import {
    useDecideMessage,
    useGetMessages,
    useGetOutreachConfig,
    useGetTemplates,
    usePrepareMessage,
    usePreviewMessage,
} from "@/hooks/api/outreach.queries";
import { showToast } from "@/lib/toast";
import { formatPhone, formatRelative, isWithinDays } from "@/utils/format.utils";
import { contactsForChannel, templatesForChannel } from "@/utils/outreach.utils";

const NO_TEMPLATE = "none";
const FALLBACK_SUBJECT_MAX = 200;
const FALLBACK_BODY_MAX = 2000;
const FALLBACK_RECENT_DAYS = 14;
const COPY_SEPARATOR = "\n\n";
const CHANNEL_ORDER: OutreachChannel[] = [OUTREACH_CHANNEL.WHATSAPP, OUTREACH_CHANNEL.EMAIL];

const NO_CONTACT_TEXT: Record<OutreachChannel, string> = {
    [OUTREACH_CHANNEL.WHATSAPP]: "This lead has no phone number to message.",
    [OUTREACH_CHANNEL.EMAIL]: "This lead has no email address that can receive mail.",
};

const OPEN_LABEL: Record<OutreachChannel, string> = {
    [OUTREACH_CHANNEL.WHATSAPP]: "Open WhatsApp",
    [OUTREACH_CHANNEL.EMAIL]: "Open mail app",
};

type TSendMessageDialogProps = {
    lead: TBusinessDetail;
    open: boolean;
    onClose: () => void;
};

type TMessageFlowProps = {
    lead: TBusinessDetail;
    onClose: () => void;
};

const describeContact = (contact: TContactPoint): string => {
    if (contact.kind === CONTACT_KIND.EMAIL) return contact.value;
    const kind = contact.kind === CONTACT_KIND.WHATSAPP || contact.whatsapp_likely ? "WhatsApp" : contact.is_mobile ? "Mobile" : "Landline";
    return `${formatPhone(contact.value)} · ${kind}`;
};

const firstChannel = (lead: TBusinessDetail): OutreachChannel =>
    CHANNEL_ORDER.find((channel) => contactsForChannel(lead.contacts, channel).length > 0) ?? OUTREACH_CHANNEL.WHATSAPP;

const MessageFlow = ({ lead, onClose }: TMessageFlowProps) => {
    const { data: config } = useGetOutreachConfig();
    const { mutateAsync: preview, isPending: isPreviewing } = usePreviewMessage();
    const { mutateAsync: prepare, isPending: isPreparing } = usePrepareMessage();
    const { mutateAsync: decide, isPending: isDeciding } = useDecideMessage();
    const { data: lastSent } = useGetMessages({ business_id: lead.id, status: MESSAGE_STATUS.SENT, limit: 1 });

    const [channel, setChannel] = useState<OutreachChannel>(() => firstChannel(lead));
    const [chosenContactId, setChosenContactId] = useState<number | null>(null);
    const [templateId, setTemplateId] = useState<number | null>(null);
    const [subject, setSubject] = useState("");
    const [body, setBody] = useState("");
    const [prepared, setPrepared] = useState<TPreparedMessage | null>(null);

    const { data: templatesData } = useGetTemplates({ channel });

    const isEmail = channel === OUTREACH_CHANNEL.EMAIL;
    const contacts = contactsForChannel(lead.contacts, channel);
    const contactId = contacts.find((contact) => contact.id === chosenContactId)?.id ?? contacts[0]?.id;
    const templates = templatesForChannel(templatesData?.data ?? [], channel);
    const subjectMax = config?.subject_max_length ?? FALLBACK_SUBJECT_MAX;
    const bodyMax = config?.body_max_length ?? FALLBACK_BODY_MAX;
    const recentDays = config?.recent_days ?? FALLBACK_RECENT_DAYS;
    const previous = lastSent?.data[0];
    const showRecentWarning = previous !== undefined && isWithinDays(previous.decided_at, recentDays);
    const canContinue = contactId !== undefined && body.trim().length > 0 && !isPreparing;
    const copyText = isEmail && subject.trim() ? `${subject.trim()}${COPY_SEPARATOR}${body.trim()}` : body.trim();
    const canCopy = body.trim().length > 0;

    const onChannelChange = (next: OutreachChannel) => {
        setChannel(next);
        setChosenContactId(null);
        setTemplateId(null);
    };

    const onTemplateChange = async (value: string) => {
        if (value === NO_TEMPLATE) {
            setTemplateId(null);
            return;
        }
        const id = Number(value);
        setTemplateId(id);
        const filled = await preview({ business_id: lead.id, template_id: id });
        setSubject(filled.subject ?? "");
        setBody(filled.body);
    };

    const copyMessage = async () => {
        try {
            await navigator.clipboard.writeText(copyText);
            showToast.success("Message copied");
        } catch {
            showToast.error("Couldn't copy to the clipboard");
        }
    };

    const continueToSend = async () => {
        if (contactId === undefined) return;
        const result = await prepare({
            business_id: lead.id,
            contact_id: contactId,
            channel,
            template_id: templateId ?? undefined,
            subject: isEmail ? subject.trim() || null : null,
            body: body.trim(),
        });
        setPrepared(result);
    };

    const markSent = async (sent: boolean) => {
        if (prepared === null) return;
        await decide({ id: prepared.id, body: { sent } });
        showToast.success(sent ? "Logged as sent" : "Not logged as sent");
        onClose();
    };

    const renderChannel = (value: OutreachChannel) => (
        <Button
            key={value}
            type="button"
            size="sm"
            variant={value === channel ? "default" : "outline"}
            onClick={() => onChannelChange(value)}
        >
            {MESSAGE_CHANNEL_LABELS[value]}
        </Button>
    );

    const renderContact = (contact: TContactPoint) => (
        <SelectItem key={contact.id} value={String(contact.id)}>
            {describeContact(contact)}
        </SelectItem>
    );

    const renderTemplate = (template: (typeof templates)[number]) => (
        <SelectItem key={template.id} value={String(template.id)}>
            {template.name}
        </SelectItem>
    );

    if (prepared !== null) {
        return (
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Send it, then tell us</DialogTitle>
                    <DialogDescription>
                        Nothing has been sent yet. Open the {isEmail ? "mail app" : "chat"}, press send there, then come back and confirm.
                    </DialogDescription>
                </DialogHeader>

                {prepared.last_sent_at && (
                    <p className="flex items-start gap-2 text-sm text-warning-foreground">
                        <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                        {prepared.last_sent_by?.full_name ?? "Someone"} already messaged this lead {formatRelative(prepared.last_sent_at)}.
                    </p>
                )}

                <div className="space-y-3">
                    <Button asChild className="w-full">
                        <a href={prepared.link} target="_blank" rel="noopener noreferrer">
                            <ExternalLink />
                            {OPEN_LABEL[prepared.channel]}
                        </a>
                    </Button>
                    <p className="text-center text-sm text-muted-foreground">Did you send it?</p>
                </div>

                <DialogFooter>
                    <Button variant="outline" disabled={isDeciding} onClick={() => markSent(false)}>
                        No, I did not send it
                    </Button>
                    <Button disabled={isDeciding} onClick={() => markSent(true)}>
                        {isDeciding ? <Loader2 className="animate-spin" /> : <Check />}
                        Yes, I sent it
                    </Button>
                </DialogFooter>
            </DialogContent>
        );
    }

    return (
        <DialogContent className="sm:max-w-xl">
            <DialogHeader>
                <DialogTitle>Message {lead.name}</DialogTitle>
                <DialogDescription>
                    Opens WhatsApp or your mail app with the text ready. You press send yourself, then confirm here so it is logged.
                </DialogDescription>
            </DialogHeader>

            {showRecentWarning && previous && (
                <p className="flex items-start gap-2 text-sm text-warning-foreground">
                    <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                    {previous.created_by?.full_name ?? "Someone"} messaged this lead {formatRelative(previous.decided_at)}. Check the history
                    before sending another.
                </p>
            )}

            <div className="space-y-4">
                <div className="flex gap-2">{CHANNEL_ORDER.map(renderChannel)}</div>

                {contacts.length === 0 ? (
                    <p className="text-sm text-muted-foreground">{NO_CONTACT_TEXT[channel]}</p>
                ) : (
                    <>
                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="space-y-1.5">
                                <Label htmlFor="message-contact">{isEmail ? "To" : "Number"}</Label>
                                <Select
                                    value={contactId === undefined ? undefined : String(contactId)}
                                    onValueChange={(value) => setChosenContactId(Number(value))}
                                >
                                    <SelectTrigger id="message-contact" className="w-full">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>{contacts.map(renderContact)}</SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="message-template">Template</Label>
                                <Select value={templateId === null ? NO_TEMPLATE : String(templateId)} onValueChange={onTemplateChange}>
                                    <SelectTrigger id="message-template" className="w-full">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value={NO_TEMPLATE}>Write my own</SelectItem>
                                        {templates.map(renderTemplate)}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {isEmail && (
                            <div className="space-y-1.5">
                                <Label htmlFor="message-subject">Subject</Label>
                                <Input
                                    id="message-subject"
                                    maxLength={subjectMax}
                                    value={subject}
                                    onChange={(event) => setSubject(event.target.value)}
                                />
                            </div>
                        )}

                        <div className="space-y-1.5">
                            <Label htmlFor="message-body">Message</Label>
                            <Textarea
                                id="message-body"
                                rows={8}
                                maxLength={bodyMax}
                                disabled={isPreviewing}
                                value={body}
                                onChange={(event) => setBody(event.target.value)}
                            />
                            <p className="text-xs text-muted-foreground">
                                Details like the business name are already filled in. Change anything you like before sending.
                            </p>
                        </div>
                    </>
                )}
            </div>

            <DialogFooter>
                <Button variant="ghost" onClick={onClose}>
                    Cancel
                </Button>
                <Button variant="outline" disabled={!canCopy} onClick={copyMessage}>
                    <Copy />
                    Copy text
                </Button>
                <Button disabled={!canContinue} onClick={continueToSend}>
                    {isPreparing && <Loader2 className="animate-spin" />}
                    Continue
                </Button>
            </DialogFooter>
        </DialogContent>
    );
};

const SendMessageDialog = ({ lead, open, onClose }: TSendMessageDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            {open && <MessageFlow lead={lead} onClose={onClose} />}
        </Dialog>
    );
};

export default SendMessageDialog;
