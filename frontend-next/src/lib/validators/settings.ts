import { z } from "zod";

export const settingsSchema = z.object({
  brandName: z.string().min(1, "Brand name is required"),
  businessDescription: z.string().min(1, "Description is required"),
  services: z.array(z.string()).min(1, "Add at least one service"),
  tone: z.string().min(1),
  offer: z.string(),
  bookingLink: z.string().url("Must be a valid URL").or(z.literal("")),
  businessHours: z.string(),
  disclosureLine: z.string().min(1, "AI disclosure line is required"),
  agentEnabled: z.boolean(),
});

export type SettingsFormValues = z.infer<typeof settingsSchema>;
