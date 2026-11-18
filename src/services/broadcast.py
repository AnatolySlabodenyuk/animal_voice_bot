import asyncio
import dataclasses
import logging
import time
from typing import Callable, Awaitable, List, Optional, Tuple

from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS: int = 3
SEND_INTERVAL: float = 0.05
PROGRESS_INTERVAL: float = 5.0


@dataclasses.dataclass
class BroadcastResult:
    total: int = 0
    sent: int = 0
    forbidden: int = 0
    unavailable: int = 0
    temporary: int = 0
    other: int = 0
    retries: int = 0

    @property
    def processed(self) -> int:
        return self.sent + self.forbidden + self.unavailable + self.temporary + self.other

    @property
    def errors(self) -> int:
        return self.forbidden + self.unavailable + self.temporary + self.other


ProgressCallback = Callable[[BroadcastResult], Awaitable[None]]


async def _safe_progress(
    callback: Optional[ProgressCallback],
    snapshot: BroadcastResult,
) -> None:
    if callback is None:
        return
    try:
        await callback(snapshot)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Progress callback raised %s; delivery continues.", type(exc).__name__)


async def run_broadcast(
    bot,
    users: List[Tuple[int, str]],
    text: str,
    on_progress: Optional[ProgressCallback] = None,
) -> BroadcastResult:
    result = BroadcastResult(total=len(users))

    snapshot = dataclasses.replace(result)
    await _safe_progress(on_progress, snapshot)
    last_progress_time = time.monotonic()

    for user_id, _username in users:
        attempt = 0
        while attempt < MAX_ATTEMPTS:
            try:
                await bot.send_message(chat_id=user_id, text=text)
                result.sent += 1
                break
            except asyncio.CancelledError:
                raise
            except TelegramRetryAfter as exc:
                attempt += 1
                retry_after = exc.retry_after if exc.retry_after and exc.retry_after > 0 else 1
                if attempt >= MAX_ATTEMPTS:
                    result.temporary += 1
                    logger.info(
                        "Recipient delivery exhausted after RetryAfter; "
                        "terminal_type=%s",
                        type(exc).__name__,
                    )
                    # RetryAfter is bot-wide: honour the cooldown before moving
                    # to the next recipient, even though this recipient is done.
                    await asyncio.sleep(retry_after)
                    break
                # Only count a retry when we are actually going to sleep and retry.
                result.retries += 1
                logger.debug(
                    "RetryAfter received; waiting %s seconds before retry attempt %s.",
                    retry_after,
                    attempt + 1,
                )
                await asyncio.sleep(retry_after)
            except (TelegramNetworkError, TelegramServerError) as exc:
                attempt += 1
                if attempt >= MAX_ATTEMPTS:
                    result.temporary += 1
                    logger.info(
                        "Recipient delivery exhausted after transient error; "
                        "terminal_type=%s",
                        type(exc).__name__,
                    )
                    break
                # Only count a retry when we are actually going to sleep and retry.
                result.retries += 1
                delay = 2 ** (attempt - 1)  # 1s, 2s
                logger.debug(
                    "Transient error on attempt %s; retrying in %s seconds; "
                    "error_type=%s",
                    attempt,
                    delay,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
            except TelegramForbiddenError as exc:
                result.forbidden += 1
                logger.info(
                    "Recipient permanently unreachable; "
                    "terminal_type=%s reason=forbidden",
                    type(exc).__name__,
                )
                break
            except TelegramNotFound as exc:
                result.unavailable += 1
                logger.info(
                    "Recipient not found; "
                    "terminal_type=%s reason=not_found",
                    type(exc).__name__,
                )
                break
            except TelegramBadRequest as exc:
                msg_lower = (exc.message or "").lower()
                if "chat not found" in msg_lower:
                    result.unavailable += 1
                    logger.info(
                        "Recipient unavailable; "
                        "terminal_type=%s reason=chat_not_found",
                        type(exc).__name__,
                    )
                else:
                    result.other += 1
                    logger.info(
                        "Recipient delivery failed with bad request; "
                        "terminal_type=%s reason=bad_request",
                        type(exc).__name__,
                    )
                break
            except Exception as exc:  # noqa: BLE001
                result.other += 1
                logger.info(
                    "Recipient delivery failed with unexpected error; "
                    "terminal_type=%s",
                    type(exc).__name__,
                )
                break

        await asyncio.sleep(SEND_INTERVAL)

        now = time.monotonic()
        if on_progress is not None and (now - last_progress_time) >= PROGRESS_INTERVAL:
            snapshot = dataclasses.replace(result)
            await _safe_progress(on_progress, snapshot)
            last_progress_time = now

    snapshot = dataclasses.replace(result)
    await _safe_progress(on_progress, snapshot)

    return result
