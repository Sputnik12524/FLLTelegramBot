from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from keybords import kb_client
from database.models import User, UserTeams
from calculator import fll_calculator
from sqlalchemy import select
from datetime import datetime
from database.models import FLLResult, User
from aiogram import types
from local_storage import local_storage
from keybords.registration_keyboard import keyboard


class FullRegister(StatesGroup):
    waiting_info = State()

class ShortRegister(StatesGroup):
    wait_info = State()


router = Router()


@router.callback_query(F.data == "register")
async def register(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Зарегистрируйтесь в системе, чтобы сохранять результаты!", reply_markup=keyboard)
    
    
@router.callback_query(F.data == "first_register")
async def first_register(callback: CallbackQuery, state: FSMContext):
    await callback.answer()    
    message1 = await callback.message.answer(
        f"Отправьте мне информацию о своей команде в таком формате:\nНазвание команды\nГород\nНомер команды\nПароль от аккаунта команды")
    
    await state.update_data(m_id = message1.message_id)


    await state.set_state(FullRegister.waiting_info)

@router.callback_query(F.data == "already_registered")
async def already_registered(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    message1 = await callback.message.answer(
        f"Отправьте мне информацию о своей команде в таком формате:\nНазвание команды\n Номер \nПароль от аккаунта команды")
    
    await state.update_data(m_id = message1.message_id)
    await state.set_state(ShortRegister.wait_info)


@router.callback_query(F.data=="back_to_menu")
async def back_register(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    del_id = data.get("m_id")
    if del_id:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=del_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")    
    
    await callback.message.edit_text(
        "Привет! Этот бот был разработан для Лиги Решений и предоставляет следующие полезные функции: ",
                                      reply_markup=kb_client)
    await state.clear()


@router.message(FullRegister.waiting_info)
async def register2(message: Message, state: FSMContext, session: AsyncSession): # session: AsyncSession ДОЛЖЕН быть здесь
    user_tg_id = message.from_user.id  # Получаем TG ID пользователя
    print(f"DEBUG: register2 - User TG ID: {user_tg_id}")
    parts = message.text.strip().split('\n')

    if len(parts) != 4:
        await message.answer(f"Неверный формат! Пример ввода: \nSputnik Original\nСанкт-Петербург\n12524\npassword1")
        return

    tn, c, num, pas = parts

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
                    UserTeams.number == numb,
                )
            )
            if team_obj:
                if team_obj.team != tn or team_obj.city != c:
                    await message.answer("Неверные данные - город или название")
                    return
                if team_obj.password != pas:
                    await message.answer("Неверный пароль :(")
                    return
            else:
                # Если команды нет, создаем её
                tn = tn.strip()
                c = c.strip()
                team_obj = UserTeams(team=tn, city=c, number=numb, password=pas)
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
                # полученных из сессии.
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
                await message.answer("Вы зарегистрированы и можете начать пользоваться ботом!\n По даному паролю любой участник команды сможет войти в аккаунт команды:)")
                await state.clear()  # Очищаем состояние после успешной регистрации

    except Exception as e:
        # Если произошла любая ошибка (например, уникальность на команде, если team не unique)
        # print(f"Ошибка при регистрации: {e}")
        await message.answer(f"Произошла ошибка при регистрации: {e}.\nПожалуйста, попробуйте еще раз.")
        print(f"ERROR in register2 for user {user_tg_id}: {e}")
        await state.clear()  # Возможно, стоит очистить состояние или вернуть пользователя назад


@router.message(ShortRegister.wait_info)
async def register3(message: Message, state: FSMContext, session: AsyncSession): # session: AsyncSession ДОЛЖЕН быть здесь
    user_tg_id = message.from_user.id  # Получаем TG ID пользователя
    print(f"DEBUG: register3 - User TG ID: {user_tg_id}")
    parts = message.text.strip().split('\n')

    if len(parts) != 3:
        await message.answer(f"Неверный формат! Пример ввода: \nSputnik Original\nНомер\npassword1")
        return

    tn, n, pas = parts

    try:
        numb = int(n)
    except ValueError:
        await message.answer("Номер команды должен быть числом. Пожалуйста, попробуйте еще раз.")
        return

    try:
        async with session.begin():
            team_obj = await session.scalar(
                select(UserTeams).where(
                    UserTeams.number == numb,
                )
            )
            if team_obj:
                if team_obj.team != tn:
                    await message.answer("Неверные данные - город или название")
                    return
                if team_obj.password != pas:
                    await message.answer("Неверный пароль :(")
                    return
            user_obj = await session.scalar(
                select(User).where(User.tg_id == user_tg_id)
            )
            if not team_obj:
                await message.answer("Команда с таким номером не найдена. Проверьте номер.")
                return


            if user_obj:
                print(
                    f"DEBUG: register3 - User {user_tg_id} found. Current team_id: {user_obj.team_id}. New team_id: {team_obj.id}")
                if user_obj.team_id == team_obj.id:
                    await message.answer("Вы уже зарегистрированы в этой команде. :)")
                else:
                    user_obj.team_id = team_obj.id
                    await message.answer(f"Ваша команда успешно обновлена на '{team_obj.team}'! :)")
                print(f"DEBUG: register3 - Team ID found/created: {team_obj.id}, Number: {team_obj.number}")
            else:
                print(f"DEBUG: register3 - User {user_tg_id} NOT found. Creating new User record.")
                user_obj = User(tg_id=user_tg_id, team_id=team_obj.id)
                session.add(user_obj)
                await message.answer("Вы зарегистрированы и можете начать пользоваться ботом!\n По даному паролю любой участник команды сможет войти в аккаунт команды:)")
                await state.clear() 

    except Exception as e:
        await message.answer(f"Произошла ошибка при регистрации: {e}.\nПожалуйста, попробуйте еще раз.")
        print(f"ERROR in register2 for user {user_tg_id}: {e}")
        await state.clear()  
