import { request } from "@/api/client/request";
import type { TApiArgs, TQueryParams } from "@/api/types/common";
import { HTTP_METHODS } from "@/constants";
import { ENDPOINTS } from "@/constants/endpoints.constants";
import type {
    TDecisionBody,
    TGetMessagesParams,
    TGetTemplatesParams,
    TPrepareBody,
    TPreviewBody,
    TTemplateBody,
    TTemplateUpdateBody,
} from "./outreach.request.types";
import type {
    TGetMessagesResponse,
    TGetTemplatesResponse,
    TMessageTemplate,
    TOutreachConfig,
    TOutreachMessage,
    TPreparedMessage,
    TPreview,
} from "./outreach.response.types";
import { OUTREACH_QUERY_KEYS } from "./queryKeys";

export const GetOutreachConfig = () => request<TOutreachConfig>({ method: HTTP_METHODS.GET, url: ENDPOINTS.OUTREACH.CONFIG });

export const GetTemplates = (params?: TGetTemplatesParams) =>
    request<TGetTemplatesResponse>({ method: HTTP_METHODS.GET, url: ENDPOINTS.OUTREACH.TEMPLATES, params: params as TQueryParams });

export const CreateTemplate = (body: TTemplateBody) =>
    request<TMessageTemplate, TTemplateBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.OUTREACH.TEMPLATES, body });

export const UpdateTemplate = ({ id, body }: TApiArgs<TTemplateUpdateBody>) =>
    request<TMessageTemplate, TTemplateUpdateBody>({ method: HTTP_METHODS.PATCH, url: ENDPOINTS.OUTREACH.template(id), body });

export const DeleteTemplate = ({ id }: TApiArgs) =>
    request<void>({ method: HTTP_METHODS.DELETE, url: ENDPOINTS.OUTREACH.template(id) });

export const PreviewMessage = (body: TPreviewBody) =>
    request<TPreview, TPreviewBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.OUTREACH.PREVIEW, body });

export const PrepareMessage = (body: TPrepareBody) =>
    request<TPreparedMessage, TPrepareBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.OUTREACH.MESSAGES, body });

export const DecideMessage = ({ id, body }: TApiArgs<TDecisionBody>) =>
    request<TOutreachMessage, TDecisionBody>({ method: HTTP_METHODS.POST, url: ENDPOINTS.OUTREACH.decision(id), body });

export const GetMessages = (params?: TGetMessagesParams) =>
    request<TGetMessagesResponse>({ method: HTTP_METHODS.GET, url: ENDPOINTS.OUTREACH.MESSAGES, params: params as TQueryParams });

export { OUTREACH_QUERY_KEYS };
