import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { showToast } from "@/lib/toast";
import { COPY_FEEDBACK_MS } from "@/constants/timing.constants";

type TCopyButtonProps = {
    value: string;
    label: string;
};

const CopyButton = ({ value, label }: TCopyButtonProps) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(value);
            setCopied(true);
            setTimeout(() => setCopied(false), COPY_FEEDBACK_MS);
        } catch {
            showToast.error("Couldn't copy to the clipboard");
        }
    };

    return (
        <Button
            variant="ghost"
            size="icon-xs"
            aria-label={`Copy ${label}`}
            onClick={handleCopy}
        >
            {copied ? <Check /> : <Copy />}
        </Button>
    );
};

export default CopyButton;
