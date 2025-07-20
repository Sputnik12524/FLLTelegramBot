from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserTeams
from calculator import fll_calculator
from sqlalchemy import select

from keybords.patent_kb import get_confirm_join_team_keyboard


class Register(StatesGroup):
    waiting_info = State()
    confirm_existing_team = State()


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


"""@router.callback_query(F.data == "register")
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
"""

@router.callback_query(F.data == "register")
async def register(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()

    user_tg_id = callback.from_user.id
    user = await session.scalar(select(User).where(User.tg_id == user_tg_id))

    if user and user.team_id:
        existing_team = await session.scalar(select(UserTeams).where(UserTeams.id == user.team_id))
        await callback.message.answer(
            f"Вы уже зарегистрированы в команде №{existing_team.number}. Если вы хотите сменить команду, свяжитесь с администратором.")
        await state.clear()
        return

    await state.set_state(Register.waiting_info)
    await callback.message.answer(
        "Пожалуйста, введите номер команды, название и город через запятую (например: 12524, Sputnik Original, Санкт-Петербург)")


@router.message(Register.waiting_info)
async def register2(message: Message, state: FSMContext, session: AsyncSession):
    input_text = message.text.strip()
    parts = input_text.split(',', 2)

    if len(parts) != 3:
        await message.answer(
            "Пожалуйста, введите номер команды, название и город через запятую (например: 12524, Sputnik Original, Санкт-Петербург)")
        return

    try:
        team_number = int(parts[0].strip())
        if team_number <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Неверный номер команды. Введите целое положительное число.")
        return

    team_name = parts[1].strip()
    if not team_name:
        await message.answer("Название команды не может быть пустым.")
        return
    if len(team_name) > 50:
        await message.answer("Название команды слишком длинное (макс. 50 символов).")
        return

    existing_team = await session.scalar(select(UserTeams).where(UserTeams.number == team_number))

    if existing_team:
        await state.update_data(proposed_team_number=team_number)
        await state.set_state(Register.confirm_existing_team)

        confirmation_text = (
            f"Команда №{team_number} ('{existing_team.team}') уже существует в базе данных.\n"
            f"Вы уверены, что хотите зарегистрироваться именно в эту команду?"
        )
        # !!! ВЫЗЫВАЕМ БЕЗ ПАРАМЕТРОВ АДМИНОВ !!!
        await message.answer(confirmation_text, reply_markup=get_confirm_join_team_keyboard())
        return

    await state.clear()
    await _register_new_team_and_user(message, session, team_number, team_name, team_city=parts[2].strip())


# --- ХЭНДЛЕРЫ ДЛЯ ПОДТВЕРЖДЕНИЯ СУЩЕСТВУЮЩЕЙ КОМАНДЫ (confirm_join_existing_team без изменений) ---
@router.callback_query(F.data == "confirm_join_existing_team", Register.confirm_existing_team)
async def confirm_join_existing_team(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer("Подтверждено!")

    data = await state.get_data()
    team_number = data.get('proposed_team_number')

    if team_number is None:
        await callback.message.answer("Произошла ошибка, пожалуйста, попробуйте зарегистрироваться снова.")
        await state.clear()
        return

    existing_team = await session.scalar(select(UserTeams).where(UserTeams.number == team_number))

    if existing_team:
        user_tg_id = callback.from_user.id
        user = await session.scalar(select(User).where(User.tg_id == user_tg_id))

        if user:
            user.team_id = existing_team.id
            await session.commit()
            await callback.message.answer(
                f"Вы успешно зарегистрированы в команду №{team_number} ('{existing_team.team}')!")
        else:
            await callback.message.answer("Ваш пользователь не найден. Пожалуйста, свяжитесь с администратором.")
            await session.rollback()
    else:
        await callback.message.answer(
            "Команда не найдена. Пожалуйста, попробуйте снова или свяжитесь с администратором.")
        await session.rollback()

    await state.clear()


@router.callback_query(F.data == "cancel_join_existing_team", Register.confirm_existing_team)
async def cancel_join_existing_team(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Регистрация отменена.")
    await state.clear() # Очищаем состояние

    admin_info_text = "Регистрация в команду отменена.\n" \
                      "Если вы считаете, что это ошибка, или хотите зарегистрировать новую команду с этим номером, " \
                      "пожалуйста, свяжитесь с администраторами:\n"

    if ADMIN_TELEGRAM_USERNAMES:
        admin_info_text += "\n".join(ADMIN_TELEGRAM_USERNAMES)


async def _register_new_team_and_user(message: Message, session: AsyncSession, team_number: int, team_name: str, team_city: str):
    new_team = UserTeams(number=team_number, team=team_name, city=team_city)
    session.add(new_team)
    await session.flush() # Получаем ID новой команды до коммита

    user = await session.scalar(select(User).where(User.tg_id == message.from_user.id))
    if user:
        user.team_id = new_team.id
        await session.commit()
        await message.answer(f"Вы успешно зарегистрировали команду №{team_number} ('{team_name}') и были к ней прикреплены!")
    else:
        await session.rollback() # Откатываем создание команды, если нет пользователя
        await message.answer("Ошибка: Пользователь не найден. Пожалуйста, свяжитесь с администратором.")

# !!! УДАЛЯЕМ ЭТОТ ХЭНДЛЕР !!!
# @router.callback_query(F.data.startswith("contact_admin_"), Register.confirm_existing_team)
# async def contact_admin_callback(callback: types.CallbackQuery):
#     await callback.answer()
#     admin_id = callback.data.split("_")[-1]
#     await callback.message.answer(
#         f"Чтобы связаться с администратором, напишите ему в Telegram, используя его ID: `{admin_id}`\n"
#         f"Или, если у вас есть его имя пользователя, то `@имя_пользователя`.",
#         parse_mode="Markdown"
#     )
