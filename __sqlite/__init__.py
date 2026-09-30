from .modifyTable import modifyTable
from .spatialiteConnection import spatialiteConnection

# Check sql version
def checkSQL() -> None:
    import sqlite3
    if sqlite3.sqlite_version_info < (3, 35, 0):
        raise RuntimeError(
            "SQLite >= 3.35 is required."
        )
    return

checkSQL()