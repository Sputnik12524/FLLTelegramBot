import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base

async_engine = create_async_engine('sqlite+aiosqlite:///mydatabase.db',
                                   echo=False)  # echo=True для логирования SQL-запросов
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


async def proceed_schemas():
    """Создает таблицы в базе данных, если их нет."""
    print("async_main() was started")
    print(f"Using DB file at: {os.path.abspath('mydatabase.db')}")
    try:
        async with async_engine.begin() as conn:
            # Только создаем недостающие таблицы. НИЧЕГО не удаляем.
            await conn.run_sync(Base.metadata.create_all)
        print("База данных готова. Недостающие таблицы созданы (если были).")
    except Exception as e:
        print(f"Произошла ошибка: {e}")


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
