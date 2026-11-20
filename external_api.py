import httpx

try:
    response = httpx.get(
        "https://jsonplaceholder.typicode.com/users",
        timeout=5
    )

    response.raise_for_status()

    users = response.json()

    for user in users:
        print(user["name"])

except httpx.HTTPStatusError as e:
    print("API error:", e)

except httpx.RequestError as e:
    print("Connection error:", e)