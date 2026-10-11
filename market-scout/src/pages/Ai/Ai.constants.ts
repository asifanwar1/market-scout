export const AI_PAGE_TITLE = "AI assistant";

export const AI_PAGE_DESCRIPTION =
    "Lets the app read a lead's website and say what the business does, which segment it fits and how well it matches your ideal customer.";

export const HOW_IT_WORKS = [
    "It only runs when someone presses Analyze on a lead or on selected leads. Nothing is analysed automatically.",
    "For each lead it sends Anthropic the business name, address and listing details, and the visible text of its website (home page and an About page when there is one, at most about 8,000 characters). Contact details such as phone numbers and emails are not sent on purpose, but may appear in a website's text.",
    "Websites that disallow automated reading in robots.txt are not read. Leads without a website are skipped at no cost.",
    "Every lead shows what it cost, and the assistant stops by itself before it could pass this month's budget. Costs are worked out from the token counts Anthropic reports and the prices listed here, so check them against your Anthropic bill.",
    "Results are advice. They never change a lead's segment or score unless someone presses 'Use this segment'.",
];

export const KEY_HELP = "Create a key in the Anthropic Console (console.anthropic.com). It is stored encrypted and can't be shown again.";
export const KEY_PLACEHOLDER = "Paste your Anthropic API key";
export const REMOVE_KEY_TITLE = "Remove the saved key?";
export const REMOVE_KEY_DESCRIPTION = "The AI assistant will be switched off unless a key is also set on the server.";
export const BUDGET_HELP = "The assistant stops when this month's spending would pass this amount. It resets on the 1st of each month.";
export const MODEL_HELP =
    "Larger models read more carefully and cost more per lead. For a simple rating, Sonnet or Haiku is usually plenty. Prices are per million tokens.";
