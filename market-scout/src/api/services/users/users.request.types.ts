import type { UserRole } from "@/constants/user-role.constants";

export type TGetUsersParams = {
    page?: number;
    limit?: number;
    search?: string;
    role?: UserRole;
};

export type TCreateUserBody = {
    email: string;
    full_name: string;
    role: UserRole;
    password: string;
};

// Send only what changed. Changing role, active state or password ends that user's sessions.
export type TUpdateUserBody = {
    full_name?: string;
    role?: UserRole;
    is_active?: boolean;
    password?: string;
};
