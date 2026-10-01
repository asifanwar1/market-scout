import { z } from "zod";

import { DO_NOT_CONTACT_KIND, REASON_MAX_LENGTH } from "../DoNotContact.constants";

export const addDoNotContactSchema = z
    .object({
        kind: z.enum([DO_NOT_CONTACT_KIND.PHONE, DO_NOT_CONTACT_KIND.EMAIL]),
        value: z.string().trim().min(1, "Enter a phone number or email address"),
        reason: z.string().max(REASON_MAX_LENGTH, `At most ${REASON_MAX_LENGTH} characters`),
    })
    .superRefine((values, ctx) => {
        if (values.kind === DO_NOT_CONTACT_KIND.EMAIL && !z.email().safeParse(values.value).success) {
            ctx.addIssue({ code: "custom", path: ["value"], message: "Enter a valid email address" });
        }
    });

export type TAddFormValues = z.infer<typeof addDoNotContactSchema>;

export const EMPTY_ADD_FORM: TAddFormValues = { kind: DO_NOT_CONTACT_KIND.PHONE, value: "", reason: "" };
