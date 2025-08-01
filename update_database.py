import asyncio
from database.engine import proceed_schemas

async def update_database():
    """Обновляет базу данных с новой таблицей FLLResult"""
    print("Обновление базы данных...")
    await proceed_schemas()
    print("База данных успешно обновлена!")

if __name__ == "__main__":
    asyncio.run(update_database()) 