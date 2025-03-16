from typing import Annotated, Any
import typer
import subprocess
import shutil
import os
import pathlib
import toml
from rich.console import Console
import contextlib


@contextlib.contextmanager
def modified_environ(*remove: Any, **update: Any):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or tuple()

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        # Only try to remove keys that exist to avoid KeyError
        [env.pop(k, None) for k in remove_after]

app = typer.Typer()

TEMPLATE_DIRECTORY = pathlib.Path(__file__).parent.parent / "_templates" 

def copy_template_files(
        destination: pathlib.Path,
        source: pathlib.Path = TEMPLATE_DIRECTORY / "default"
    ) -> None:
    """Copy template files to the specified path.
    
    Args:
        destination: Destination directory for template files
        source: Source directory containing template files (defaults to "default" template)
    """
    destination.mkdir(exist_ok=True, parents=True)
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True
    )

class ChangeDirectory:
    """Context manager for changing the current working directory and returning to the previous directory on exit."""
    
    def __init__(self, new_path: pathlib.Path | str):
        """Initialize with the path to change to.
        
        Args:
            new_path: Path to change the current working directory to
        """
        self.new_path = new_path
        self.previous_path: pathlib.Path = pathlib.Path.cwd()
        
    def __enter__(self) -> 'ChangeDirectory':
        """Change to the new directory and store the previous directory."""
        self.previous_path = pathlib.Path.cwd()
        os.chdir(self.new_path)
        return self
        
    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None) -> None:
        """Return to the previous directory."""
        os.chdir(str(self.previous_path))


@app.command()
def init(
    name: Annotated[str, typer.Argument()],
):
    try:
        with modified_environ(UV_VENV_SEED="True"):
            subprocess.run(['uv', 'init', name, '--lib', '--no-workspace', '--quiet', '--no-readme'], check=True)
    except subprocess.CalledProcessError:
        raise typer.Exit(code=1)
    # Change the working directory to the newly created project directory
    with ChangeDirectory(pathlib.Path.cwd() / name):
        copy_template_files(pathlib.Path.cwd())
        
        console = Console()
        with console.status("[bold green]Installing prefect...", spinner="dots"):
            try:
                subprocess.run(['uv', 'add', 'prefect', '--no-active'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                subprocess.run(['uv', 'add', 'prefect', '--offline', '--no-cache', '--frozen'], check=True)
        
        # TODO: Pull these settings into some external config file
        with open('pyproject.toml', 'r') as f:
            pyproject = toml.load(f) # type: ignore
            pyproject['tool']={}
            pyproject["tool"]["prefect"] = {
                'home': './.prefect',
                'profiles_path': './.prefect/profiles.toml',
            }
            with open('pyproject.toml', 'w') as f:
                toml.dump(pyproject, f)
        console.print(f"[bold green]Success! Created {name} at {pathlib.Path.cwd()}")

if __name__ == "__main__":
    app()
