import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { TColumnMapping, TImportOptions } from "@/api/services/imports/imports.request.types";
import type { TImportPreview } from "@/api/services/imports/imports.response.types";
import { useGetGeographyTree, useGetProfile, useGetProfiles, useGetSources } from "@/hooks/api/catalog.queries";
import { useCreateImport, usePreviewImport } from "@/hooks/api/imports.queries";
import { getBlobErrorMessage } from "@/utils/download.utils";
import { APP_ROUTES } from "@/routes/appRoutes";
import { showToast } from "@/lib/toast";
import { EMPTY_MAPPING, defaultLabel, importProblem, mappingFromSuggestion } from "./importForm";

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
    const [lookupContacts, setLookupContacts] = useState(false);
    const { data: sourcesData } = useGetSources();
    // Looking phones up needs the Overture data on the server; offer it only when it is there.
    const overture = sourcesData?.data.find((source) => source.key === "overture");
    const canLookUp = overture?.is_available ?? false;
    const lookupOn = lookupContacts && canLookUp;

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
            setFileError(await getBlobErrorMessage(error));
        }
    };

    const resetFile = () => {
        setFile(null);
        setPreview(null);
        setFileError(null);
    };

    const problem = importProblem({ mapping, label, profileId, requireContact, lookupContacts: lookupOn });

    const start = async () => {
        if (!file || profileId === undefined || problem) return;
        const options: TImportOptions = {
            label: label.trim(),
            profile_id: profileId,
            segment_slug: segmentSlug,
            default_geography_id: cityId,
            require_contact: requireContact,
            lookup_contacts: lookupOn,
            mapping,
        };
        const created = await createImport({ file, options });
        showToast.success(`Importing ${created.rows_to_import} rows from ${created.label}`);
        navigate(APP_ROUTES.IMPORTS_DETAILS.replace(":id", String(created.id)));
    };

    return {
        file,
        preview,
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
        setProfileId: (id: number) => {
            setChosenProfileId(id);
            setSegmentSlug(null); // another profile has other business types
        },
        segments: profile?.segments ?? [],
        segmentSlug,
        setSegmentSlug,
        geographyTree,
        cityId,
        setCityId,
        requireContact,
        setRequireContact,
        lookupContacts: lookupOn,
        setLookupContacts,
        canLookUp,
        problem,
        isStarting,
        start,
    };
};

export type TNewImport = ReturnType<typeof useNewImport>;
