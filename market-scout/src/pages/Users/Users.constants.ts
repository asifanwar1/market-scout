import { USER_ROLE } from "@/constants";

export const USERS_PAGE_TITLE = "Users";

export const USERS_PAGE_DESCRIPTION =
    "The people who can sign in. Sales accounts work the leads; admins also run searches and manage settings.";

export const USER_ROLE_FILTER_VALUES = [USER_ROLE.ADMIN, USER_ROLE.SALES] as const;

export const ROLE_LABELS = {
    [USER_ROLE.ADMIN]: "Admin",
    [USER_ROLE.SALES]: "Sales",
} as const;

export const ROLE_BADGE_CLASSES = {
    [USER_ROLE.ADMIN]: "bg-accent text-accent-foreground",
    [USER_ROLE.SALES]: "bg-secondary text-secondary-foreground",
} as const;

export const ACTIVE_BADGE_CLASS = "bg-success text-success-foreground";
export const INACTIVE_BADGE_CLASS = "bg-muted text-muted-foreground";

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;
export const NAME_MIN_LENGTH = 2;
export const NAME_MAX_LENGTH = 100;
export const PASSWORD_SPECIAL_CHARACTER_PATTERN = /[!@#$%^&*()\-_=+[\]{}|;:,.<>?]/;
