import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import {
    EMAIL_INVALID,
    EMAIL_REQUIRED,
    PASSWORD_REQUIRED,
} from "@/constants";
import { useLogin } from "@/hooks/api/auth.queries";
import { APP_ROUTES } from "@/routes/appRoutes";

const loginSchema = z.object({
    email: z.string().min(1, EMAIL_REQUIRED).email(EMAIL_INVALID),
    password: z.string().min(1, PASSWORD_REQUIRED),
});

export type TLoginFormValues = z.infer<typeof loginSchema>;

export const useLoginPage = () => {
    "use no memo"; // React Hook Form + React Compiler: see README

    const navigate = useNavigate();
    const { mutateAsync: login, isPending } = useLogin();

    const form = useForm<TLoginFormValues>({
        resolver: zodResolver(loginSchema),
        defaultValues: { email: "", password: "" },
    });

    const onSubmit = form.handleSubmit(async (values) => {
        try {
            await login(values);
            navigate(APP_ROUTES.ROOT, { replace: true });
        } catch {
            // The API client already showed why (wrong password, server down, ...).
            form.setValue("password", "");
        }
    });

    return { form, onSubmit, isPending };
};
