import type { UserModel } from "@/api/models/user.model";

export type TTokenResponse = {
    access_token: string;
    refresh_token: string;
    token_type: string;
};

export type TMeResponse = UserModel;

export type TMessageResponse = {
    message: string;
};
