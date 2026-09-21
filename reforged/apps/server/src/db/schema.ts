import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';

export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  email: text('email').notNull().unique(),
  passwordHash: text('password_hash').notNull(),
  createdAt: integer('created_at').notNull(),
});

export const runs = sqliteTable('runs', {
  id: text('id').primaryKey(),
  userId: text('user_id').notNull(),
  status: text('status').notNull(), // 'active' | 'won' | 'lost'
  wins: integer('wins').notNull(),
  losses: integer('losses').notNull(),
  roundNumber: integer('round_number').notNull(),
  gold: integer('gold').notNull(),
  level: integer('level').notNull(),
  xp: integer('xp').notNull(),
  unitsJson: text('units_json').notNull(),
  boardJson: text('board_json').notNull(),
  augmentsPickedJson: text('augments_picked_json').notNull(),
  augmentPending: integer('augment_pending').notNull(), // 0 | 1
  augmentOffersJson: text('augment_offers_json'), // nullable — null when no offers pending
  shopOffersJson: text('shop_offers_json').notNull(),
  shopLocked: integer('shop_locked').notNull(), // 0 | 1
  createdAt: integer('created_at').notNull(),
  updatedAt: integer('updated_at').notNull(),
});

export const combatLogs = sqliteTable('combat_logs', {
  id: text('id').primaryKey(),
  runId: text('run_id').notNull(),
  seed: integer('seed').notNull(),
  eventsJson: text('events_json').notNull(),
  winner: text('winner').notNull(), // 'player' | 'enemy'
  createdAt: integer('created_at').notNull(),
});
