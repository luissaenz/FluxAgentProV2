"""SSE Connection Manager — Handles active Server-Sent Events streams by organization."""

import asyncio
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SSEConnectionManager:
    """Singleton manager for SSE connections by org_id.

    Allows broadcasting events (task updates, tool results) to all clients
    connected to a specific organization.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SSEConnectionManager, cls).__new__(cls)
            cls._instance.active_connections: Dict[str, List[asyncio.Queue]] = {}
        return cls._instance

    async def connect(self, org_id: str) -> asyncio.Queue:
        """Create a new queue for an org_id connection."""
        queue = asyncio.Queue()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = []
        self.active_connections[org_id].append(queue)
        logger.info(
            "SSE Client connected to org_id=%s. Active connections for org: %d",
            org_id,
            len(self.active_connections[org_id]),
        )
        return queue

    async def disconnect(self, org_id: str, queue: asyncio.Queue):
        """Remove a queue for an org_id on disconnect."""
        if org_id in self.active_connections:
            if queue in self.active_connections[org_id]:
                self.active_connections[org_id].remove(queue)
            if not self.active_connections[org_id]:
                del self.active_connections[org_id]
        logger.info("SSE Client disconnected from org_id=%s", org_id)

    async def broadcast(self, org_id: str, event_type: str, data: dict):
        """Push an event to all active queues of an organization."""
        if org_id not in self.active_connections:
            return

        # Prepare message for sse-starlette format
        message = {"event": event_type, "data": data}

        logger.debug("Broadcasting event '%s' to org_id=%s", event_type, org_id)
        for queue in self.active_connections[org_id]:
            await queue.put(message)


# Global singleton instance
sse_manager = SSEConnectionManager()
