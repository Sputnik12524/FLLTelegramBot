from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserTeams
from calculator import fll_calculator
from sqlalchemy import select


class Register(StatesGroup):
    waiting_info = State()


router = Router()


@router.callback_query(F.data == "missions")
async def show_calculator(callback: CallbackQuery):
    """Показывает главное меню калькулятора"""
    try:
        keyboard = fll_calculator.get_main_keyboard(callback.from_user.id)
        await callback.message.edit_text(
            "🧮 **Калькулятор миссий FLL - Богатый урожай**\n\n"
            "Выберите миссию для установки очков:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("calc_mission_"))
async def show_mission_detail(callback: CallbackQuery):
    """Показывает детали конкретной миссии"""
    try:
        mission_id = callback.data.replace("calc_", "")
        if mission_id not in fll_calculator.missions:
            await callback.answer("Миссия не найдена!")
            return

        mission_name = fll_calculator.missions[mission_id]["name"]
        current_score = fll_calculator.get_mission_score(callback.from_user.id, mission_id)

        keyboard = fll_calculator.get_mission_keyboard(mission_id)
        await callback.message.edit_text(
            f"🎯 **{mission_name}**\n\n"
            f"Текущие очки: {current_score}\n"
            f"Выберите количество очков:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("calc_set_"))
async def set_mission_score(callback: CallbackQuery):
    """Устанавливает очки за миссию"""
    try:
        parts = callback.data.split("_")
        if len(parts) < 4:
            await callback.answer("Неверный формат данных!")
            return

        mission_id = f"{parts[2]}_{parts[3]}"
        score = int(parts[4])

        success = fll_calculator.set_mission_score(callback.from_user.id, mission_id, score)

        if success:
            keyboard = fll_calculator.get_main_keyboard(callback.from_user.id)
            await callback.message.edit_text(
                "🧮 **Калькулятор миссий FLL - Богатый урожай**\n\n"
                "Выберите миссию для установки очков:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback.answer(f"✅ Очки обновлены: {score}")
        else:
            await callback.answer("❌ Ошибка при установке очков!")
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data == "calc_total")
async def show_total_score(callback: CallbackQuery):
    """Показывает детальную разбивку очков"""
    try:
        breakdown = fll_calculator.get_score_breakdown(callback.from_user.id)
        keyboard = fll_calculator.get_main_keyboard(callback.from_user.id)

        await callback.message.edit_text(
            breakdown,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data == "calc_reset")
async def reset_calculator(callback: CallbackQuery):
    """Сбрасывает все очки"""
    try:
        fll_calculator.reset_scores(callback.from_user.id)
        keyboard = fll_calculator.get_main_keyboard(callback.from_user.id)

        await callback.message.edit_text(
            "🧮 **Калькулятор миссий FLL - Богатый урожай**\n\n"
            "Все очки сброшены! Выберите миссию для установки очков:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer("🔄 Калькулятор сброшен!")
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data == "calc_back")
async def back_to_calculator(callback: CallbackQuery):
    """Возвращает к главному меню калькулятора"""
    try:
        keyboard = fll_calculator.get_main_keyboard(callback.from_user.id)
        await callback.message.edit_text(
            "🧮 **Калькулятор миссий FLL - Богатый урожай**\n\n"
            "Выберите миссию для установки очков:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data == "register")
async def register(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Зарегистрируйтесь в системе, чтобы сохранять результаты!")
    await callback.message.answer(
        f"Отправьте мне информацию о своей команде в таком формате:\nНазвание\nГород\nНомер")
    await state.set_state(Register.waiting_info)


@router.message(Register.waiting_info)
async def register2(message: Message, state: FSMContext, session: AsyncSession): # session: AsyncSession ДОЛЖЕН быть здесь
    user_tg_id = message.from_user.id  # Получаем TG ID пользователя
    print(f"DEBUG: register2 - User TG ID: {user_tg_id}")
    parts = message.text.strip().split('\n')

    if len(parts) != 3:
        await message.answer(f"Неверный формат! Пример ввода: \nSputnik Original\nСанкт-Петербург\n12524")
        return

    tn, c, num = parts

    try:
        numb = int(num)
    except ValueError:
        await message.answer("Номер команды должен быть числом. Пожалуйста, попробуйте еще раз.")
        return

    try:
        async with session.begin():
            # Ищем или создаем команду
            team_obj = await session.scalar(
                select(UserTeams).where(
                    UserTeams.team == tn,
                    UserTeams.city == c,
                    UserTeams.number == numb
                )
            )
            if not team_obj:
                # Если команды нет, создаем её
                team_obj = UserTeams(team=tn, city=c, number=numb)
                print(f"DEBUG: register2 - Team not found, creating new: {tn}, {c}, {numb}")
                session.add(team_obj)
                await session.flush()  # flush() нужен, чтобы получить team.id для новой команды


            # Ищем или обновляем пользователя
            user_obj = await session.scalar(
                select(User).where(User.tg_id == user_tg_id)
            )

            if user_obj:
                # Пользователь уже существует. Обновляем его team_id.
                # SQLAlchemy автоматически отслеживает изменения в объектах,
                # полученных из сессии. session.add() здесь НЕ НУЖЕН,
                # если объект уже управляем сессией.
                print(
                    f"DEBUG: register2 - User {user_tg_id} found. Current team_id: {user_obj.team_id}. New team_id: {team_obj.id}")
                if user_obj.team_id == team_obj.id:
                    await message.answer("Вы уже зарегистрированы в этой команде. :)")
                else:
                    user_obj.team_id = team_obj.id
                    await message.answer(f"Ваша команда успешно обновлена на '{team_obj.team}'! :)")
                print(f"DEBUG: register2 - Team ID found/created: {team_obj.id}, Number: {team_obj.number}")
            else:
                # Пользователь не существует в БД (это странно, если /start работает),
                # создаем нового.
                print(f"DEBUG: register2 - User {user_tg_id} NOT found. Creating new User record.")
                user_obj = User(tg_id=user_tg_id, team_id=team_obj.id)
                session.add(user_obj)
                await message.answer("Вы зарегистрированы и можете начать пользоваться ботом! :)")
                await state.clear()  # Очищаем состояние после успешной регистрации

    except Exception as e:
        # Если произошла любая ошибка (например, уникальность на команде, если team не unique)
        # print(f"Ошибка при регистрации: {e}")
        await message.answer(f"Произошла ошибка при регистрации: {e}.\nПожалуйста, попробуйте еще раз.")
        print(f"ERROR in register2 for user {user_tg_id}: {e}")
        await state.clear()  # Возможно, стоит очистить состояние или вернуть пользователя назад

