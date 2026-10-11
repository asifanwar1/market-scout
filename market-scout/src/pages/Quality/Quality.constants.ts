export const QUALITY_PAGE_TITLE = "Data quality";

export const QUALITY_PAGE_DESCRIPTION =
    "Keep the lead list honest: review businesses that may be listed twice, see which traits go with winning deals, and decide whether contacts are checked automatically.";

export const DUPLICATES_TITLE = "Possible duplicates";

export const DUPLICATES_DESCRIPTION =
    "The app merges obvious matches by itself. These are pairs it was not sure about. Merging moves everything onto the lead you keep and cannot be undone.";

export const DUPLICATES_EMPTY = "Nothing to review.";

export const SCAN_LABEL = "Look through existing leads";

export const SCAN_HELP = "Finds pairs among leads that are already stored. New leads are compared as they arrive.";

export const MERGE_TITLE = "Merge these two leads?";

export const MERGE_DESCRIPTION =
    "The other lead is deleted. Its contacts, history, tasks, notes and do-not-contact marks move to the lead you keep. This cannot be undone.";

export const SCORING_TITLE = "What goes with winning";

export const SCORING_DESCRIPTION =
    "Compares leads you closed as won with those you closed as lost. It shows what you worked, so a pattern here is a hint rather than proof.";

export const SCORING_NEEDS_MORE = "Close at least {needed} deals (won or lost) before the app suggests changes. {closed} so far.";

export const APPLY_TITLE = "Apply the suggested weights?";

export const APPLY_DESCRIPTION =
    "The profile's score weights change and every lead's score for it is recalculated. You can undo this afterwards.";

export const SETTINGS_TITLE = "Contact checks";

export const SETTINGS_DESCRIPTION =
    "Contact checks look up email domains and visit websites once, lightly. They can run on selected leads from the Leads page, or automatically for the leads a run touched.";

export const AFTER_RUNS_LABEL = "Check contacts automatically after each run";

export const PER_RUN_LABEL = "Most leads to check after one run";

export const PAGE_SIZE = 5;

export const SIDE_LABELS = { a: "Lead A", b: "Lead B" } as const;
