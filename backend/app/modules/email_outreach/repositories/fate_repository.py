"""
FATE Matrix Repository
All database operations for the fate_matrix table.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class FateRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_rule(self, sector: str, designation: str):
        """
        Tries to find an exact match in the FATE Matrix.
        Returns None if not found.
        """
        query = text("""
            SELECT * FROM fate_matrix 
            WHERE LOWER(sector) = LOWER(:sector) 
            AND LOWER(designation_role) = LOWER(:designation)
            LIMIT 1;
        """)
        result = await self.db.execute(query, {"sector": sector, "designation": designation})
        return result.fetchone()

    async def get_rule_by_sector(self, sector: str):
        """
        Fallback: Get any rule matching the sector.
        Used when exact sector+designation match is not found.
        """
        query = text("""
            SELECT * FROM fate_matrix 
            WHERE LOWER(sector) = LOWER(:sector) 
            LIMIT 1;
        """)
        result = await self.db.execute(query, {"sector": sector})
        return result.fetchone()
