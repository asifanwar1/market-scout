import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Config from "@/Config";
import {
    HELP_CURL,
    HELP_ENDPOINTS,
    HELP_INTRO,
    HELP_TITLE,
    HELP_WEBHOOK_TEXT,
    HELP_WEBHOOK_TITLE,
} from "../Integrations.constants";

const BASE_PLACEHOLDER = "{base}";

const ApiHelpCard = () => {
    const example = HELP_CURL.replace(BASE_PLACEHOLDER, Config.API_URL);

    const renderEndpoint = (endpoint: (typeof HELP_ENDPOINTS)[number]) => (
        <li key={`${endpoint.method}${endpoint.path}`} className="space-y-0.5">
            <p className="font-mono text-xs">
                <span className="font-semibold">{endpoint.method}</span> /public{endpoint.path}
            </p>
            <p className="text-xs text-muted-foreground">{endpoint.note}</p>
        </li>
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>{HELP_TITLE}</CardTitle>
                <CardDescription>{HELP_INTRO}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
                <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">{example}</pre>
                <ul className="space-y-3">{HELP_ENDPOINTS.map(renderEndpoint)}</ul>
                <div className="space-y-1">
                    <h3 className="text-sm font-medium">{HELP_WEBHOOK_TITLE}</h3>
                    <p className="text-sm text-muted-foreground">{HELP_WEBHOOK_TEXT}</p>
                </div>
            </CardContent>
        </Card>
    );
};

export default ApiHelpCard;
