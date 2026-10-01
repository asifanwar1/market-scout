import axios from "axios";

import Config from "../../Config";
import { REQUEST_TIMEOUT_MS } from "@/constants/timing.constants";

const axiosInstance: ReturnType<typeof axios.create> = axios.create({
    baseURL: Config.API_URL,
    timeout: REQUEST_TIMEOUT_MS,
});

export default axiosInstance;
