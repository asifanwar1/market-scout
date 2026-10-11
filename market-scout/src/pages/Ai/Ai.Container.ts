import { useState, type ChangeEvent } from "react";

import { AI_API_KEY_MIN_LENGTH, AI_BUDGET_MAX } from "@/constants/ai.constants";
import { useGetAiSettings, useTestAi, useUpdateAiSettings } from "@/hooks/api/ai.queries";
import { showToast } from "@/lib/toast";
import { formatAiCost } from "@/utils/ai.utils";
import { parseAmount, percentOf } from "@/utils/pipeline.utils";

export const useAiPage = () => {
    const { data: settings, isPending } = useGetAiSettings();
    const { mutateAsync: update, isPending: isSaving } = useUpdateAiSettings();
    const { mutateAsync: runKeyTest, isPending: isTesting, data: testResult, reset: resetTest } = useTestAi();

    const [apiKey, setApiKey] = useState("");
    const [budgetText, setBudgetText] = useState<string | null>(null);
    const [isRemoveOpen, setIsRemoveOpen] = useState(false);

    const models = settings?.models ?? [];
    const selectedModel = models.find((model) => model.id === settings?.model);
    const budgetValue = budgetText ?? String(settings?.monthly_budget_usd ?? "");
    const parsedBudget = parseAmount(budgetValue);
    const isBudgetValid = parsedBudget !== null && parsedBudget <= AI_BUDGET_MAX;
    const isBudgetChanged = budgetText !== null && parsedBudget !== settings?.monthly_budget_usd;
    const canSaveBudget = isBudgetValid && isBudgetChanged && !isSaving;
    const canSaveKey = apiKey.trim().length >= AI_API_KEY_MIN_LENGTH && !isSaving;
    const canTest = settings?.has_key === true && !isTesting;
    const canEnable = settings?.has_key === true;
    const spentPercent = settings ? percentOf(settings.spent_this_month_usd, settings.monthly_budget_usd) : 0;
    const spentText = settings ? formatAiCost(settings.spent_this_month_usd) : "";
    const remainingText = settings ? formatAiCost(settings.remaining_usd) : "";
    const hasSavedKey = settings?.key_source === "saved";

    const onApiKeyChange = (event: ChangeEvent<HTMLInputElement>) => {
        setApiKey(event.target.value);
    };

    const onBudgetChange = (event: ChangeEvent<HTMLInputElement>) => {
        setBudgetText(event.target.value);
    };

    const saveKey = async () => {
        await update({ api_key: apiKey.trim() });
        setApiKey("");
        resetTest();
        showToast.success("Key saved");
    };

    const openRemove = () => {
        setIsRemoveOpen(true);
    };

    const closeRemove = () => {
        setIsRemoveOpen(false);
    };

    const confirmRemove = async () => {
        await update({ clear_api_key: true });
        setIsRemoveOpen(false);
        resetTest();
        showToast.success("Saved key removed");
    };

    const toggleEnabled = async (enabled: boolean) => {
        await update({ is_enabled: enabled });
        showToast.success(enabled ? "AI assistant switched on" : "AI assistant switched off");
    };

    const changeModel = async (modelId: string) => {
        await update({ model: modelId });
        resetTest();
        showToast.success("Model changed");
    };

    const saveBudget = async () => {
        if (parsedBudget === null) return;
        await update({ monthly_budget_usd: parsedBudget });
        setBudgetText(null);
        showToast.success("Budget saved");
    };

    const testKey = async () => {
        await runKeyTest();
    };

    return {
        settings,
        isPending,
        isSaving,
        isTesting,
        testResult,
        models,
        selectedModel,
        apiKey,
        budgetValue,
        isBudgetValid,
        canSaveBudget,
        canSaveKey,
        canTest,
        canEnable,
        hasSavedKey,
        spentPercent,
        spentText,
        remainingText,
        isRemoveOpen,
        onApiKeyChange,
        onBudgetChange,
        saveKey,
        openRemove,
        closeRemove,
        confirmRemove,
        toggleEnabled,
        changeModel,
        saveBudget,
        testKey,
    };
};
