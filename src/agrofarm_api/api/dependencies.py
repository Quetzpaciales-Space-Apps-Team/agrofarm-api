from typing import Protocol

from fastapi import Request

from agrofarm_api.repositories.database import Database


class DatabaseProtocol(Protocol):
    def ping(self) -> bool: ...


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database
