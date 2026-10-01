import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { TColumnMapping, TImportOptions } from "@/api/services/imports/imports.request.types";
import type { TImportPreview } from "@/api/services/imports/imports.response.types";
import { useGetGeographyTree, useGetProfile, useGetProfiles, useGetSources } from "@/hooks/api/catalog.queries";
import { useCreateImport, usePreviewImport } from "@/hooks/api/imports.queries";
import { GENERIC_ERROR_MESSAGE } from "@/constants/Validation-messages.constants";
import { getBlobErrorMessage } from "@/utils/download.utils";
import { APP_ROUTES } from "@/routes/appRoutes";
import { showToast } from "@/lib/toast";
import { OVERTURE_SOURCE_KEY } from "@/constants/source.constants";
import { EMPTY_MAPPING, defaultLabel, importProblem, mappingFromSuggestion } from "./importForm";

type TImportFormState = {
    label: string;
    profileId: number;
    segmentSlug: string | null;
    cityId: number | null;
    requireContact: boolean;
    lookupContacts: boolean;
    mapping: TColumnMapping;
};

const buildImportPayload = (form: TImportFormState): TImportOptions => ({
    label: form.label.trim(),
    profile_id: form.profileId,
    segment_slug: form.segmentSlug,
    default_geography_id: form.cityId,
    require_contact: form.requireContact,
    lookup_contacts: form.lookupContacts,
    mapping: form.mapping,
});

export const useNewImport = () => {
    const navigate = useNavigate();

    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<TImportPreview | null>(null);
    const [fileError, setFileError] = useState<string | null>(null);
    const { mutateAsync: previewFile, isPending: isReading } = usePreviewImport();
    const { mutateAsync: createImport, isPending: isStarting } = useCreateImport();

    const [mapping, setMapping] = useState<TColumnMapping>(EMPTY_MAPPING);
    const [label, setLabel] = useState("");
    const [chosenProfileId, setChosenProfileId] = useState<number | null>(null);
    const [segmentSlug, setSegmentSlug] = useState<string | null>(null);
    const [cityId, setCityId] = useState<number | null>(null);
    const [requireContact, setRequireContact] = useState(true);
    const [isLookupRequested, setLookupContacts] = useState(false);
    const { data: sourcesData } = useGetSources();
    const overture = sourcesData?.data.find((source) => source.key === OVERTURE_SOURCE_KEY);
    const canLookUp = overture?.is_available ?? false;
    const lookupContacts = isLookupRequested && canLookUp;

    const { data: profilesData } = useGetProfiles();
    const profiles = profilesData?.data ?? [];
    const profileId = chosenProfileId ?? profiles[0]?.id;
    const { data: profile } = useGetProfile(profileId);
    const { data: geographyTree = [] } = useGetGeographyTree();

    const chooseFile = async (chosen: File) => {
        setFile(chosen);
        setPreview(null);
        setFileError(null);
        try {
            const result = await previewFile({ file: chosen });
            setPreview(result);
            setMapping(mappingFromSuggestion(result.suggested_mapping));
            setLabel(defaultLabel(chosen.name));
        } catch (error) {
            setFile(null);
            setFileError(error instanceof Error ? await getBlobErrorMessage(error) : GENERIC_ERROR_MESSAGE);
        }
    };

    const resetFile = () => {
        setFile(null);
        setPreview(null);
        setFileError(null);
    };

    const problem = importProblem({ mapping, label, profileId, requireContact, lookupContacts });
    const hasPreview = preview !== null;
    const isStartDisabled = !hasPreview || problem !== null || isStarting;
    const segments = profile?.segments ?? [];

    const setProfileId = (id: number) => {
        setChosenProfileId(id);
        setSegmentSlug(null);
    };

    const start = async () => {
        if (!file || profileId === undefined || problem) return;
        const options = buildImportPayload({
            label,
            profileId,
            segmentSlug,
            cityId,
            requireContact,
            lookupContacts,
            mapping,
        });
        const created = await createImport({ file, options });
        showToast.success(`Importing ${created.rows_to_import} rows from ${created.label}`);
        navigate(APP_ROUTES.IMPORTS_DETAILS.replace(":id", String(created.id)));
    };

    return {
        file,
        preview,
        hasPreview,
        fileError,
        isReading,
        chooseFile,
        resetFile,
        mapping,
        setMapping,
        label,
        setLabel,
        profiles,
        profileId,
        setProfileId,
        segments,
        segmentSlug,
        setSegmentSlug,
        geographyTree,
        cityId,
        setCityId,
        requireContact,
        setRequireContact,
        lookupContacts,
        setLookupContacts,
        canLookUp,
        problem,
        isStarting,
        isStartDisabled,
        start,
    };
};

export type TNewImport = ReturnType<typeof useNewImport>;
