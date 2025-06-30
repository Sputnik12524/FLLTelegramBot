from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

engine = create_async_engine('sqlite+aiosqlite:///mydatabase.db', echo=True)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__= 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger)

class User_Teams(Base):
    __tablename__ = 'teams'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    team: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    number: Mapped[int] = mapped_column()

class Record(Base):
    __tablename__ = 'records'
    id: Mapped[int] = mapped_column(primary_key=True)
    r_team: Mapped[int] = mapped_column(ForeignKey('teams.id'))
    result: Mapped[int] = mapped_column()
    video_id: Mapped[int] = mapped_column(BigInteger)

async def async_main():
    print("async_main() was started")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("База данных успешно создана.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
