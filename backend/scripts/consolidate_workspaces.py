import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.project import ResearchProject
from app.models.question import ResearchQuestion


async def consolidate_workspaces():
    async with AsyncSessionLocal() as session:
        projects = (await session.scalars(select(ResearchProject).order_by(ResearchProject.created_at.desc()))).all()
        grouped: dict[str, list[ResearchProject]] = {}
        for p in projects:
            key = p.name.strip().lower()
            grouped.setdefault(key, []).append(p)

        consolidated_groups = 0
        deleted_count = 0

        for key, p_list in grouped.items():
            if len(p_list) > 1:
                # Primary is the first (newest created)
                primary = p_list[0]
                duplicates = p_list[1:]
                print(f"Consolidating {len(duplicates)} duplicate(s) for '{primary.name}' into ID: {primary.id}")

                for dup in duplicates:
                    # Move questions from dup to primary
                    await session.execute(
                        update(ResearchQuestion)
                        .where(ResearchQuestion.project_id == dup.id)
                        .values(project_id=primary.id)
                    )
                    # Delete the duplicate project
                    await session.delete(dup)
                    deleted_count += 1

                consolidated_groups += 1

        await session.commit()
        print(f"Consolidation complete: {consolidated_groups} duplicate groups merged, {deleted_count} duplicate project rows removed.")


if __name__ == "__main__":
    asyncio.run(consolidate_workspaces())
