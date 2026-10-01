import { useState } from "react";

import type { TGeographyNode } from "@/api/services/geographies/geographies.response.types";
import { useGetGeographyTree } from "@/hooks/api/catalog.queries";
import { useDeleteGeography } from "@/hooks/api/geographies.queries";
import { showToast } from "@/lib/toast";
import { LOCATION_KIND } from "./Locations.constants";
import type { TLocationDialogState } from "./Locations.types";

export const useLocationsPage = () => {
    const { data: tree = [], isPending } = useGetGeographyTree();
    const { mutateAsync: deleteGeography, isPending: isDeleting } = useDeleteGeography();

    const [dialog, setDialog] = useState<TLocationDialogState | null>(null);
    const [toDelete, setToDelete] = useState<TGeographyNode | null>(null);

    const country = tree[0];
    const provinces = tree.flatMap((node) => node.children);
    const hasProvinces = provinces.length > 0;
    const isDeleteOpen = toDelete !== null;
    const deleteTitle = `Delete ${toDelete?.name ?? ""}?`;
    const isDeletingCity = toDelete?.level === LOCATION_KIND.CITY;

    const addProvince = () => {
        if (country) setDialog({ kind: LOCATION_KIND.PROVINCE, node: null, parent: country });
    };

    const addCity = (province: TGeographyNode) => {
        setDialog({ kind: LOCATION_KIND.CITY, node: null, parent: province });
    };

    const editProvince = (province: TGeographyNode) => {
        setDialog({ kind: LOCATION_KIND.PROVINCE, node: province, parent: null });
    };

    const editCity = (city: TGeographyNode) => {
        setDialog({ kind: LOCATION_KIND.CITY, node: city, parent: null });
    };

    const askToDelete = (node: TGeographyNode) => {
        setToDelete(node);
    };

    const closeDialog = () => {
        setDialog(null);
    };

    const cancelDelete = () => {
        setToDelete(null);
    };

    const confirmDelete = async () => {
        if (!toDelete) return;
        await deleteGeography(toDelete.id);
        showToast.success(`${toDelete.name} deleted`);
        setToDelete(null);
    };

    return {
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
    };
};
