import { Dialog, DialogContent } from "@/components/ui/dialog";
import type { TLocationDialogState } from "../Locations.types";
import LocationForm from "./LocationForm";

type TLocationDialogProps = {
    state: TLocationDialogState | null;
    onClose: () => void;
};

const LocationDialog = ({ state, onClose }: TLocationDialogProps) => {
    const onOpenChange = (next: boolean) => {
        if (!next) onClose();
    };

    return (
        <Dialog open={state !== null} onOpenChange={onOpenChange}>
            <DialogContent>{state && <LocationForm key={`${state.kind}-${state.node?.id ?? "new"}`} state={state} onClose={onClose} />}</DialogContent>
        </Dialog>
    );
};

export default LocationDialog;
