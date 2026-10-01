import { Dialog, DialogContent } from "@/components/ui/dialog";
import AddDoNotContactForm from "./AddDoNotContactForm";

type TAddDoNotContactDialogProps = {
    open: boolean;
    onClose: () => void;
};

const AddDoNotContactDialog = ({ open, onClose }: TAddDoNotContactDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <AddDoNotContactForm onClose={onClose} />
            </DialogContent>
        </Dialog>
    );
};

export default AddDoNotContactDialog;
