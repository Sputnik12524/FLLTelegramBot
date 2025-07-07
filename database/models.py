from sqlalchemy import BigInteger, String, ForeignKey, Integer, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
import os

engine = create_async_engine('sqlite+aiosqlite:///mydatabase.db', echo=True)
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger)
    team_id: Mapped[int] = mapped_column(ForeignKey('teams.id'))


class User_Teams(Base):
    __tablename__ = 'teams'

    id: Mapped[int] = mapped_column(primary_key=True)
    team: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    number: Mapped[int] = mapped_column(Integer)


class Record(Base):
    __tablename__ = 'records'
    id: Mapped[int] = mapped_column(primary_key=True)
    r_team: Mapped[int] = mapped_column(ForeignKey('teams.id'))
    result: Mapped[int] = mapped_column(Integer)
    video_id: Mapped[int] = mapped_column(BigInteger)


class Patent(Base):
    __tablename__ = 'patents'
    id: Mapped[int] = mapped_column(primary_key=True)

    team_number: Mapped[int] = mapped_column(ForeignKey('teams.id'))
    caption: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(250))
    missions: Mapped[list] = mapped_column(JSON)
    image_id: Mapped[str] = mapped_column(JSON)
    video_id: Mapped[str] = mapped_column(JSON)
    approved: Mapped[bool] = mapped_column(Boolean)


async def async_main():
    print("async_main() was started")
    print(f"Using DB file at: {os.path.abspath('mydatabase.db')}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print("База данных успешно создана.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
