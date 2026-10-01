import { z } from "zod";

import { EMAIL_INVALID, EMAIL_REQUIRED, PASSWORD_REQUIRED } from "@/constants";

export const loginSchema = z.object({
    email: z.string().min(1, EMAIL_REQUIRED).email(EMAIL_INVALID),
    password: z.string().min(1, PASSWORD_REQUIRED),
});

export type TLoginFormValues = z.infer<typeof loginSchema>;

export const EMPTY_LOGIN_FORM: TLoginFormValues = { email: "", password: "" };
