import type { FastifyReply } from 'fastify';
import { RunForbiddenError, RunNotFoundError } from '../services/runService.js';
import { BenchFullError, InsufficientGoldError, InvalidShopOfferError, UnitInstanceNotFoundError as ShopUnitNotFoundError } from '../services/shopService.js';
import { BoardCapacityError, UnitInstanceNotFoundError as BoardUnitNotFoundError } from '../services/boardService.js';
import { InvalidAugmentChoiceError, NoAugmentPendingError } from '../services/augmentService.js';
import { AugmentPendingError, EmptyBoardError, RunNotActiveError } from '../services/combatOrchestrator.js';

const NOT_FOUND = [RunNotFoundError, ShopUnitNotFoundError, BoardUnitNotFoundError];
const FORBIDDEN = [RunForbiddenError];
const BAD_REQUEST = [
  InsufficientGoldError,
  BenchFullError,
  InvalidShopOfferError,
  BoardCapacityError,
  NoAugmentPendingError,
  InvalidAugmentChoiceError,
  RunNotActiveError,
  AugmentPendingError,
  EmptyBoardError,
];

export function handleServiceError(reply: FastifyReply, err: unknown): void {
  if (NOT_FOUND.some((E) => err instanceof E)) {
    reply.code(404).send({ error: (err as Error).message || 'not_found' });
    return;
  }
  if (FORBIDDEN.some((E) => err instanceof E)) {
    reply.code(403).send({ error: 'forbidden' });
    return;
  }
  if (BAD_REQUEST.some((E) => err instanceof E)) {
    reply.code(400).send({ error: (err as Error).constructor.name });
    return;
  }
  throw err;
}
