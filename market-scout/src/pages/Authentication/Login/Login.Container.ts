"use no memo";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import type { TLoginBody } from "@/api/services/auth/auth.request.types";
import { useLogin } from "@/hooks/api/auth.queries";
import { APP_ROUTES } from "@/routes/appRoutes";
import { EMPTY_LOGIN_FORM, loginSchema, type TLoginFormValues } from "./Login.schema";

const CLEARED_PASSWORD = "";

const buildLoginPayload = (values: TLoginFormValues): TLoginBody => ({
    email: values.email,
    password: values.password,
});

export const useLoginPage = () => {
    const navigate = useNavigate();
    const { mutateAsync: login, isPending } = useLogin();

    const form = useForm<TLoginFormValues>({
        resolver: zodResolver(loginSchema),
        defaultValues: EMPTY_LOGIN_FORM,
    });

    const onSubmit = form.handleSubmit(async (values) => {
        try {
            await login(buildLoginPayload(values));
            navigate(APP_ROUTES.ROOT, { replace: true });
        } catch {
            form.setValue("password", CLEARED_PASSWORD);
        }
    });

    return {
        form,
        onSubmit,
        isPending,
    };
};
