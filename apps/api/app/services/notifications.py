"""Best-effort worker wakeup; PostgreSQL remains the source of recoverable jobs."""

import asyncio
import redis
import redis.asyncio as aioredis
from app.config import settings


def wake_worker():
    try:
        with redis.Redis.from_url(
            settings().redis_url, socket_connect_timeout=0.2, socket_timeout=0.2
        ) as client:
            client.lpush("ugc:generation-wakeup", "1")
            client.ltrim("ugc:generation-wakeup", 0, 999)
    except redis.RedisError:
        pass  # Durable DB admission already committed; worker polling recovers this notification.


async def wait_for_work():
    try:
        async with aioredis.Redis.from_url(
            settings().redis_url, socket_connect_timeout=0.2, socket_timeout=2
        ) as client:
            await client.blpop("ugc:generation-wakeup", timeout=1)
    except redis.RedisError:
        await asyncio.sleep(1)
