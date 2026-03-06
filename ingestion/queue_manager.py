"""Thread-safe in-memory queue with a bounded capacity for pipeline items."""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MAXLEN = 30


class QueueManager:
    """Bounded FIFO queue backed by :class:`collections.deque`.

    When the queue is at capacity the *oldest* item is silently evicted and a
    warning is logged so that operators can detect back-pressure.

    Args:
        maxlen: Maximum number of items the queue can hold.  Defaults to 30.
    """

    def __init__(self, maxlen: int = _DEFAULT_MAXLEN) -> None:
        self._maxlen: int = maxlen
        self._queue: deque[Any] = deque(maxlen=maxlen)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, item: Any) -> None:
        """Add *item* to the back of the queue.

        If the queue is already at capacity the oldest item will be dropped by
        the underlying :class:`~collections.deque` and a warning is emitted.

        Args:
            item: Any serialisable object to enqueue.
        """
        if self.is_full():
            logger.warning(
                "QueueManager at capacity (%d/%d) – oldest item will be dropped",
                len(self._queue),
                self._maxlen,
            )
        self._queue.append(item)

    def dequeue(self) -> Optional[Any]:
        """Remove and return the oldest item from the queue.

        Returns:
            The oldest item, or ``None`` if the queue is empty.
        """
        if not self._queue:
            return None
        return self._queue.popleft()

    def size(self) -> int:
        """Return the current number of items in the queue.

        Returns:
            Queue length as a non-negative integer.
        """
        return len(self._queue)

    def is_full(self) -> bool:
        """Check whether the queue has reached its maximum capacity.

        Returns:
            ``True`` if the queue is full, ``False`` otherwise.
        """
        return len(self._queue) >= self._maxlen

    def clear(self) -> None:
        """Remove all items from the queue."""
        self._queue.clear()
        logger.debug("QueueManager cleared")
