import { z } from 'zod';
import { RankInfoSchema } from './rank.js';

export const UserProfileSchema = z.object({
  discordId: z.string(),
  username: z.string(),
  avatarUrl: z.string().nullable(),
  rank: RankInfoSchema,
});
export type UserProfile = z.infer<typeof UserProfileSchema>;
