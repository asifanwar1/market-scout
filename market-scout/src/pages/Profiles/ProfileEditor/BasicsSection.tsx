import { Controller, useFormContext } from "react-hook-form";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { TProfileFormValues } from "./profileForm";

const BasicsSection = () => {
    "use no memo"; // React Hook Form + React Compiler: see README

    const {
        register,
        control,
        formState: { errors },
    } = useFormContext<TProfileFormValues>();

    return (
        <Card>
            <CardHeader>
                <CardTitle>Basics</CardTitle>
                <CardDescription>
                    A profile is one industry to look for (for example solar, or water pumps).
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-1.5">
                    <Label htmlFor="profile-name">Name</Label>
                    <Input id="profile-name" aria-invalid={!!errors.name} {...register("name")} />
                    {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
                </div>

                <div className="space-y-1.5">
                    <Label htmlFor="profile-description">Description</Label>
                    <Textarea
                        id="profile-description"
                        rows={2}
                        maxLength={500}
                        placeholder="Who you're looking for, in a sentence"
                        {...register("description")}
                    />
                </div>

                <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
                    <div>
                        <Label htmlFor="profile-active">Active</Label>
                        <p className="text-xs text-muted-foreground">
                            Switched-off profiles can't be used for new runs. Switch off instead of deleting to keep the history.
                        </p>
                    </div>
                    <Controller
                        control={control}
                        name="isActive"
                        render={({ field }) => (
                            <Switch id="profile-active" checked={field.value} onCheckedChange={field.onChange} />
                        )}
                    />
                </div>
            </CardContent>
        </Card>
    );
};

export default BasicsSection;
