import { describe, expect, it } from 'vitest';
import { roundIncome } from '../src/services/economyService.js';

describe('economy', () => {
  it('pays half of the previous round income, including interest', () => {
    expect(roundIncome(0)).toBe(12);
    expect(roundIncome(50)).toBe(15);
    expect(roundIncome(100)).toBe(17);
    expect(roundIncome(250)).toBe(25);
  });
});
