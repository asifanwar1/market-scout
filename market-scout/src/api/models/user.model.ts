import type { UserRole } from "@/constants/user-role.constants";

export type UserModel = {
    id: number;
    email: string;
    full_name: string;
    role: UserRole;
    is_active: boolean;
    created_at: string;
    updated_at?: string | null;
};
