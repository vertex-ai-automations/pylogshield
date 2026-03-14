# __main__.py
"""Entrypoint for `python -m pylogshield` and the `custom-logger` CLI command."""

from pylogshield.cli import app


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
