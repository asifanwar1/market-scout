import axios from "axios";

import Config from "../../Config";

const axiosInstance: ReturnType<typeof axios.create> = axios.create({
    baseURL: Config.API_URL,
    timeout: 30000,
});

export default axiosInstance;
