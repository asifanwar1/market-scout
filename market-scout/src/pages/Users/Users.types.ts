import type { UserRole } from "@/constants";

export type TUserRoleFilter = UserRole | null;

export type TUserFormValues = {
    email: string;
    full_name: string;
    role: UserRole;
    is_active: boolean;
    password: string;
};
