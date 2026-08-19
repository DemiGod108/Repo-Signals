import asyncio
connected_clients: dict[int, set[asyncio.Queue]] = {}