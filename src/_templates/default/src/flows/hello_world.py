from prefect import flow
from tasks.hello import hello
import asyncio


@flow
async def hello_world(names: list[str] = ['Ford Prefect', 'Marvin']) -> list[str]:
    return hello.map(names).result()


if __name__ == '__main__':
    asyncio.run(hello_world())