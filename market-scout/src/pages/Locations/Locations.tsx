import { MapPin, Plus } from "lucide-react";

import type { TGeographyNode } from "@/api/services/geographies/geographies.response.types";
import ConfirmationModal from "@/components/custom/ConfirmationModal";
import EmptyState from "@/components/custom/EmptyState";
import Loading from "@/components/custom/Loading";
import PageHeader from "@/components/custom/PageHeader";
import { Button } from "@/components/ui/button";
import LocationDialog from "./Components/LocationDialog";
import ProvinceCard from "./Components/ProvinceCard";
import { LOCATIONS_PAGE_DESCRIPTION, LOCATIONS_PAGE_TITLE } from "./Locations.constants";
import { useLocationsPage } from "./Locations.Container";

const DELETE_CITY_WARNING = "Leads already found there are kept but no longer show a city. Past runs keep its name.";
const DELETE_PROVINCE_NOTE = "This province has no cities left, so nothing else is affected.";

const Locations = () => {
    const {
        country,
        provinces,
        hasProvinces,
        isPending,
        isDeleting,
        isDeleteOpen,
        isDeletingCity,
        deleteTitle,
        dialog,
        addProvince,
        addCity,
        editProvince,
        editCity,
        askToDelete,
        closeDialog,
        cancelDelete,
        confirmDelete,
    } = useLocationsPage();

    const renderProvince = (province: TGeographyNode) => (
        <ProvinceCard
            key={province.id}
            province={province}
            onAddCity={addCity}
            onEditProvince={editProvince}
            onEditCity={editCity}
            onDelete={askToDelete}
        />
    );

    if (isPending) return <Loading />;

    return (
        <div className="space-y-6">
            <PageHeader
                title={LOCATIONS_PAGE_TITLE}
                description={LOCATIONS_PAGE_DESCRIPTION}
                actions={
                    country && (
                        <Button onClick={addProvince}>
                            <Plus />
                            Add province
                        </Button>
                    )
                }
            />

            {!hasProvinces && (
                <EmptyState
                    icon={MapPin}
                    title="No locations yet"
                    description="Load the defaults with `python -m scripts.seed` on the server, or add locations here."
                />
            )}

            {provinces.map(renderProvince)}

            <LocationDialog state={dialog} onClose={closeDialog} />

            <ConfirmationModal
                open={isDeleteOpen}
                destructive
                title={deleteTitle}
                description={isDeletingCity ? DELETE_CITY_WARNING : DELETE_PROVINCE_NOTE}
                confirmText="Delete"
                isLoading={isDeleting}
                onConfirm={confirmDelete}
                onClose={cancelDelete}
            />
        </div>
    );
};

export default Locations;
