import sqlite3
from typing import Any

# Modify table
class modifyTable(sqlite3.Cursor):
    def addFields(self, tableName: str, *fields: tuple[str, str, Any, bool]) -> None:
        """
        fields: field name, field type, initial value, wheter index
        """
        self.execute("PRAGMA table_info({})".format(tableName))
        existingColumns = [col[1] for col in self.fetchall()]
        for field in fields:
            fieldName, colType, initialValue, whetherIndex = field
            if fieldName not in existingColumns:
                if initialValue is not None:
                    self.execute(
                        f"""
                        ALTER TABLE {tableName}
                        ADD COLUMN {fieldName} {colType}
                        DEFAULT {initialValue}
                        """
                    )
                else:
                    self.execute(
                        f"""
                        ALTER TABLE {tableName}
                        ADD COLUMN {fieldName} {colType}
                        """
                    )
            if whetherIndex:
                self.addIndex(fieldName, tableName)

        return
    
    def addIndex(self, fieldName: str, tableName: str) -> None:
        self.execute(f"CREATE INDEX IF NOT EXISTS idx_{fieldName} ON {tableName} ({fieldName})")

        return
    
    def dropFields(self, tableName: str, *fieldNames: str) -> None:
        self.execute(f"PRAGMA table_info({tableName})")
        columns = [row[1] for row in self.fetchall()]
        self.execute(f"PRAGMA index_list({tableName})")
        indexes = [row[1] for row in self.fetchall()]
        for fieldName in fieldNames:
            # Del index if exists
            self.__dropIndexByList(fieldName, indexes)
            # Del column
            if fieldName in columns:
                self.execute(
                    f"""
                    ALTER TABLE {tableName}
                    DROP COLUMN {fieldName}
                    """
                )
        
        self.execute("VACUUM")

        return
    
    def dropIndex(self, tableName: str, *fieldNames: str) -> None:
        self.execute(f"PRAGMA table_info({tableName})")
        columns = [row[1] for row in self.fetchall()]
        self.execute(f"PRAGMA index_list({tableName})")
        indexes = [row[1] for row in self.fetchall()]
        for fieldName in fieldNames:
            if fieldName in columns: self.__dropIndexByList(fieldName, indexes)
        
        self.execute("VACUUM")

        return
    
    def __dropIndexByList(self, fieldName: str, indexes: list) -> None:
        relatedIndexes = []
        for index in indexes:
            self.execute(f"PRAGMA index_info({index})")
            indexColumns = [row[2] for row in self.fetchall()]
            if fieldName in indexColumns:
                relatedIndexes.append(index)
        
        for index in relatedIndexes:
            self.execute(f"DROP INDEX {index}")

        return None
    
    def dropTable(self, tableName: str) -> None:
        self.execute(f"DROP TABLE IF EXISTS \"{tableName}\"")
        self.execute(f"DELETE FROM gpkg_contents WHERE table_name = '{tableName}'")
        self.execute(f"DELETE FROM gpkg_geometry_columns WHERE table_name = '{tableName}'")
        self.execute("VACUUM")

        return