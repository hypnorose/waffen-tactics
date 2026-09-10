"""Typed failures shared by combat callers.

Combat failures are intentionally separate from legitimate combat outcomes. The
internal detail is suitable for server logs; callers should expose only the
stable code/message pair to clients.
"""


class CombatError(RuntimeError):
    code = "combat_error"
    retriable = True
    safe_message = "Combat could not be completed. Please try again."

    def __init__(self, detail: str, *, cause: Exception | None = None):
        super().__init__(detail)
        self.detail = detail
        self.cause = cause


class InvalidCombatInputError(CombatError):
    code = "invalid_combat_input"
    retriable = False
    safe_message = "Combat data is invalid. Please refresh and try again."


class CombatExecutionError(CombatError):
    code = "combat_execution_failed"
    retriable = True
    safe_message = "Combat could not be completed. Please try again."
