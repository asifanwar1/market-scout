import { z } from "zod";

import { USER_ROLE } from "@/constants";
import {
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PASSWORD_SPECIAL_CHARACTER_PATTERN,
} from "../Users.constants";
import type { TUserFormValues } from "../Users.types";

const UPPERCASE_PATTERN = /[A-Z]/;
const DIGIT_PATTERN = /\d/;

const passwordRule = z
    .string()
    .min(PASSWORD_MIN_LENGTH, `At least ${PASSWORD_MIN_LENGTH} characters`)
    .max(PASSWORD_MAX_LENGTH, `At most ${PASSWORD_MAX_LENGTH} characters`)
    .refine((value) => UPPERCASE_PATTERN.test(value), "Include an uppercase letter")
    .refine((value) => DIGIT_PATTERN.test(value), "Include a digit")
    .refine((value) => PASSWORD_SPECIAL_CHARACTER_PATTERN.test(value), "Include a special character such as ! or #");

const baseFields = {
    full_name: z
        .string()
        .trim()
        .min(NAME_MIN_LENGTH, `At least ${NAME_MIN_LENGTH} characters`)
        .max(NAME_MAX_LENGTH, `At most ${NAME_MAX_LENGTH} characters`),
    role: z.enum([USER_ROLE.ADMIN, USER_ROLE.SALES]),
    is_active: z.boolean(),
};

export const createUserSchema = z.object({
    ...baseFields,
    email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
    password: passwordRule,
});

export const editUserSchema = z.object({
    ...baseFields,
    email: z.string(),
    password: z.string().refine((value) => value === "" || passwordRule.safeParse(value).success, {
        message: `At least ${PASSWORD_MIN_LENGTH} characters with an uppercase letter, a digit and a special character`,
    }),
});

export const EMPTY_USER_FORM: TUserFormValues = {
    email: "",
    full_name: "",
    role: USER_ROLE.SALES,
    is_active: true,
    password: "",
};
