import asyncio
import httpx


async def get_users():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://jsonplaceholder.typicode.com/users"
        )

        response.raise_for_status()

        users = response.json()

        for user in users:
            print(user["name"])


asyncio.run(get_users())