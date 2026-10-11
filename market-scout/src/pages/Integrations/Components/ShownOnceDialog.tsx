import CopyButton from "@/components/custom/CopyButton";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

type TShownOnceDialogProps = {
    value: string | null;
    title: string;
    description: string;
    label: string;
    onClose: () => void;
};

const ShownOnceDialog = ({ value, title, description, label, onClose }: TShownOnceDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={value !== null} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>{description}</DialogDescription>
                </DialogHeader>
                <div className="flex items-center gap-2">
                    <Input readOnly value={value ?? ""} aria-label={label} className="font-mono text-xs" onFocus={(event) => event.target.select()} />
                    <CopyButton value={value ?? ""} label={label} />
                </div>
                <DialogFooter>
                    <Button onClick={onClose}>I have copied it</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default ShownOnceDialog;
