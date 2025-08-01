from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import Patent, User, UserTeams, FLLResult  # Убедитесь, что User импортирован!


# from db.engine import async_session_factory # Эта строка нужна, только если функция НЕ получает session как аргумент

# Функция для добавления патента в БД
async def add_patent_to_db(
        user_tg_id: int,  # Telegram ID пользователя, кто выкладывает
        missions: List[int],  # Список номеров миссий
        caption: str,
        description: str,
        image_ids: List[str],  # Список file_id фотографий
        video_ids: List[str],  # Список file_id видео
        session: AsyncSession  # Сессия базы данных
) -> None:
    # Находим пользователя по user_tg_id
    print(f"\n--- DEBUG add_patent_to_db ---")
    print(f"Received user_tg_id PARAMETER: {user_tg_id}")  # Какое значение пришло в функцию?
    user_query = await session.execute(
        select(User).where(User.tg_id == user_tg_id)
    )
    user_obj = user_query.scalar_one_or_none()

    if user_obj is None:
        print(f"DEBUG: add_patent_to_db - User {user_tg_id} NOT found in DB. Raising ValueError.")
        raise ValueError(f"Пользователь с TG ID {user_tg_id} не найден в базе данных.")

    # Проверяем, привязан ли пользователь к команде
    if user_obj.team_id is None:
        raise ValueError(
            f"Пользователь с TG ID {user_tg_id} не привязан к команде. Невозможно добавить изобретение без команды.")

    # Получаем team_number из таблицы UserTeams, используя team_id пользователя
    team_query = await session.execute(
        select(UserTeams.number).where(UserTeams.id == user_obj.team_id)
    )
    team_number_val = team_query.scalar_one_or_none()

    if team_number_val is None:
        # Этого не должно произойти, если team_id пользователя корректен, но на всякий случай
        raise ValueError(f"Не удалось найти номер команды для team_id: {user_obj.team_id}.")

    # Создаем новый объект Patent
    new_patent = Patent(
        team_number=team_number_val,  # Используем team_number
        missions=missions,  # SQLAlchemy JSON type handles this directly
        caption=caption,
        description=description,
        image_ids=image_ids,  # SQLAlchemy JSON type handles this directly
        video_ids=video_ids,  # SQLAlchemy JSON type handles this directly
        approved=False  # Явно задаем False, хотя в модели уже есть default
    )
    session.add(new_patent)


# Функции для работы с результатами FLL калькулятора
async def save_fll_result(
        user_tg_id: int,
        mission_scores: dict,
        total_score: int,
        max_possible_score: int,
        name: str = None,
        session: AsyncSession = None
) -> FLLResult:
    """Сохраняет результат FLL калькулятора в базу данных"""
    
    # Находим пользователя и его команду
    user_query = await session.execute(
        select(User).where(User.tg_id == user_tg_id)
    )
    user_obj = user_query.scalar_one_or_none()
    
    if user_obj is None:
        raise ValueError(f"Пользователь с TG ID {user_tg_id} не найден в базе данных.")
    
    # Создаем новый результат
    new_result = FLLResult(
        user_tg_id=user_tg_id,
        team_id=user_obj.team_id,
        mission_scores=mission_scores,
        total_score=total_score,
        max_possible_score=max_possible_score,
        name=name
    )
    
    session.add(new_result)
    await session.commit()
    await session.refresh(new_result)
    
    return new_result


async def get_user_fll_results(
        user_tg_id: int,
        session: AsyncSession = None
) -> List[FLLResult]:
    """Получает все результаты пользователя"""
    
    results_query = await session.execute(
        select(FLLResult)
        .where(FLLResult.user_tg_id == user_tg_id)
        .order_by(FLLResult.created_at.desc())
    )
    
    return results_query.scalars().all()


async def get_fll_result_by_id(
        result_id: int,
        session: AsyncSession = None
) -> FLLResult:
    """Получает конкретный результат по ID"""
    
    result_query = await session.execute(
        select(FLLResult).where(FLLResult.id == result_id)
    )
    
    return result_query.scalar_one_or_none()


async def delete_fll_result(
        result_id: int,
        user_tg_id: int,
        session: AsyncSession = None
) -> bool:
    """Удаляет результат (только если он принадлежит пользователю)"""
    
    result_query = await session.execute(
        select(FLLResult)
        .where(FLLResult.id == result_id, FLLResult.user_tg_id == user_tg_id)
    )
    
    result = result_query.scalar_one_or_none()
    
    if result:
        await session.delete(result)
        await session.commit()
        return True
    
    return False
