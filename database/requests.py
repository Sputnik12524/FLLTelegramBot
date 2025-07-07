from database.models import async_session
from database.models import User, User_Teams, Record, Patent
from sqlalchemy import select, update, delete


async def add_patent(team_number, missions: list[int], caption, description, image_id, video_id) -> None:
    async with async_session() as session:
        session.add(Patent(missions=missions, caption=caption, description=description, image_id=image_id, video_id=video_id))
        await session.commit()
