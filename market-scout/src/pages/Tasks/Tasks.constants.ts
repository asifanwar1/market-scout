import { TASK_SCOPE } from "@/constants/pipeline.constants";

export const TASKS_PAGE_TITLE = "Tasks";

export const TASKS_PAGE_DESCRIPTION = "Follow-ups you have set on leads. Tick one off when it is done.";

export const TASK_SCOPE_VALUES = [
    TASK_SCOPE.OPEN,
    TASK_SCOPE.OVERDUE,
    TASK_SCOPE.TODAY,
    TASK_SCOPE.UPCOMING,
    TASK_SCOPE.DONE,
] as const;

export const MINE_LABEL = "Only mine";

export const EMPTY_TITLES: Record<(typeof TASK_SCOPE_VALUES)[number], string> = {
    [TASK_SCOPE.OPEN]: "No open follow-ups",
    [TASK_SCOPE.OVERDUE]: "Nothing overdue",
    [TASK_SCOPE.TODAY]: "Nothing due today",
    [TASK_SCOPE.UPCOMING]: "Nothing coming up",
    [TASK_SCOPE.DONE]: "Nothing finished yet",
};

export const EMPTY_DESCRIPTION = "Open a lead and add a follow-up under Follow-ups to see it here.";

export const OPEN_LEAD_LABEL = "Open lead";
