from prefect import task


@task
def hello(name: str) -> str:
    return f'Hello {name}!'