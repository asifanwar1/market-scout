export const USER_ROLE = {
    ADMIN: "admin",
    SALES: "sales",
} as const;

export type UserRole = (typeof USER_ROLE)[keyof typeof USER_ROLE];
