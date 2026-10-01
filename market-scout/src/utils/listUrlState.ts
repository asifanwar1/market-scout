import { parseAsInteger } from "nuqs";

import Config from "@/Config";
import { FIRST_PAGE } from "@/constants/pagination.constants";

export const paginationUrlState = {
    page: parseAsInteger.withDefault(FIRST_PAGE),
    size: parseAsInteger.withDefault(Config.LIMIT),
};
