import { z } from 'zod';

export const TagSchema = z.object({
  id: z.string(),
  name: z.string(),
  icon: z.string(),
});
export type Tag = z.infer<typeof TagSchema>;
