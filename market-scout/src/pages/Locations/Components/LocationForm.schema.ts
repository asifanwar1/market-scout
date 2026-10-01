import { z } from "zod";

import {
    LATITUDE_LIMIT,
    LONGITUDE_LIMIT,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    RADIUS_KM_MAX,
} from "../Locations.constants";

const NUMBER_ERROR = "Enter a number";

const nameRule = z
    .string()
    .trim()
    .min(NAME_MIN_LENGTH, `At least ${NAME_MIN_LENGTH} characters`)
    .max(NAME_MAX_LENGTH, `At most ${NAME_MAX_LENGTH} characters`);

export const provinceSchema = z.object({
    name: nameRule,
    latitude: z.number().optional(),
    longitude: z.number().optional(),
    radius_km: z.number().optional(),
});

export const citySchema = z.object({
    name: nameRule,
    latitude: z
        .number({ error: NUMBER_ERROR })
        .min(-LATITUDE_LIMIT, `Between -${LATITUDE_LIMIT} and ${LATITUDE_LIMIT}`)
        .max(LATITUDE_LIMIT, `Between -${LATITUDE_LIMIT} and ${LATITUDE_LIMIT}`),
    longitude: z
        .number({ error: NUMBER_ERROR })
        .min(-LONGITUDE_LIMIT, `Between -${LONGITUDE_LIMIT} and ${LONGITUDE_LIMIT}`)
        .max(LONGITUDE_LIMIT, `Between -${LONGITUDE_LIMIT} and ${LONGITUDE_LIMIT}`),
    radius_km: z.number({ error: NUMBER_ERROR }).gt(0, "More than 0").max(RADIUS_KM_MAX, `At most ${RADIUS_KM_MAX} km`),
});
