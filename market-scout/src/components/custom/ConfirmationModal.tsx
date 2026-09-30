import type { ReactNode } from "react";

import {
    AlertDialog,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

type TConfirmationModalProps = {
    open: boolean;
    title: string;
    description: ReactNode;
    confirmText?: string;
    cancelText?: string;
    destructive?: boolean;
    isLoading?: boolean;
    children?: ReactNode;
    onConfirm: () => void;
    onClose: () => void;
};

const ConfirmationModal = ({
    open,
    title,
    description,
    confirmText = "Confirm",
    cancelText = "Cancel",
    destructive = false,
    isLoading = false,
    children,
    onConfirm,
    onClose,
}: TConfirmationModalProps) => {
    return (
        <AlertDialog open={open} onOpenChange={(next) => !next && !isLoading && onClose()}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>{title}</AlertDialogTitle>
                    <AlertDialogDescription>{description}</AlertDialogDescription>
                </AlertDialogHeader>
                {children}
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={isLoading}>{cancelText}</AlertDialogCancel>
                    {/* A plain Button, not AlertDialogAction: that one closes the dialog on click,
                        which would hide it before the request finishes. */}
                    <Button
                        variant={destructive ? "destructive" : "default"}
                        disabled={isLoading}
                        onClick={onConfirm}
                    >
                        {isLoading ? "Working…" : confirmText}
                    </Button>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
};

export default ConfirmationModal;
