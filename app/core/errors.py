# app/core/errors.py
"""Domain errors that API routes translate into HTTP responses."""


class GraphAreaError(Exception):
    """A requested point lies outside the area this instance serves."""
