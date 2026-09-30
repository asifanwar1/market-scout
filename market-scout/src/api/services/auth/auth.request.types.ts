export type TLoginBody = {
    email: string;
    password: string;
};

export type TChangePasswordBody = {
    current_password: string;
    new_password: string;
};
