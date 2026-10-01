import { Dialog, DialogContent } from "@/components/ui/dialog";
import type { UserModel } from "@/api/models/user.model";
import UserForm from "./UserForm";

type TUserDialogProps = {
    open: boolean;
    user: UserModel | null;
    onClose: () => void;
};

const UserDialog = ({ open, user, onClose }: TUserDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <UserForm user={user} onClose={onClose} />
            </DialogContent>
        </Dialog>
    );
};

export default UserDialog;
