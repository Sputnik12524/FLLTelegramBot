from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo, InputMediaDocument
import contextlib
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from typing import List

from database.models import User, Improvement
from keybords.improvement_kb import (
    get_improvement_main_keyboard,
    get_improvement_type_keyboard,
    get_improvement_confirm_keyboard,
    get_improvement_view_keyboard,
    get_improvement_list_keyboard,
    get_improvement_edit_keyboard
)
from keybords.keybord_client import kb_client

router = Router()

# Состояния для FSM
class ImprovementStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_files = State()
    waiting_for_edit_description = State()
    waiting_for_edit_files = State()

# Временное хранилище для данных доработки
improvement_temp_data = {}

@router.callback_query(F.data == "changes")
async def show_improvement_menu(callback: CallbackQuery):
    """Показывает главное меню доработок"""
    try:
        keyboard = get_improvement_main_keyboard()
        await callback.message.edit_text(
            "🔧 **Мои доработки**\n\n"
            "Здесь вы можете:\n"
            "• 📸 Добавить фото вашего робота\n"
            "• 💻 Загрузить код\n"
            "• 📋 Просмотреть все ваши доработки\n\n"
            "Выберите действие:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data == "improvement_main")
async def back_to_improvement_menu(callback: CallbackQuery):
    """Возврат к главному меню доработок"""
    await show_improvement_menu(callback)

@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат к главному меню бота"""
    try:
        await callback.message.edit_text(
            "Главное меню бота:",
            reply_markup=kb_client
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data.regexp(r"^improvement_add_(robot|code|other)$"))
async def start_adding_improvement(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс добавления доработки"""
    try:
        improvement_type = callback.data.replace("improvement_add_", "")
        
        # Сохраняем тип доработки в состоянии
        await state.update_data(improvement_type=improvement_type)
        
        # Очищаем временные данные
        user_id = callback.from_user.id
        if user_id in improvement_temp_data:
            del improvement_temp_data[user_id]
        
        # Шаг 1: запрашиваем название
        await state.set_state(ImprovementStates.waiting_for_title)
        
        type_names = {
            "robot": "робота",
            "code": "кода",
            "other": "доработки"
        }
        
        await callback.message.edit_text(
            f"🏷️ **Название {type_names.get(improvement_type, 'доработки')}**\n\n"
            f"Введите короткое название (до 100 символов):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="improvement_main")]
            ])
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")
@router.message(ImprovementStates.waiting_for_title)
async def handle_improvement_title(message: Message, state: FSMContext):
    """Сохраняет название и запрашивает описание"""
    try:
        title = (message.text or "").strip()
        if not title:
            await message.answer("❌ Пожалуйста, введите название!")
            return
        if len(title) > 100:
            await message.answer("❌ Название слишком длинное (максимум 100 символов).")
            return
        await state.update_data(title=title)
        
        # Переходим к описанию
        await state.set_state(ImprovementStates.waiting_for_description)
        await message.answer(
            "📝 **Описание**\n\nОпишите вашу доработку (что изменилось, какие проблемы решены):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="improvement_main")]
            ])
        )
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@router.message(ImprovementStates.waiting_for_description)
async def handle_improvement_description(message: Message, state: FSMContext):
    """Обрабатывает описание доработки"""
    try:
        description = message.text
        
        # Сохраняем описание в состоянии
        await state.update_data(description=description)
        
        # Переходим к загрузке файлов
        await state.set_state(ImprovementStates.waiting_for_files)
        
        await message.answer(
            "📸 **Загрузка файлов**\n\n"
            "Теперь отправьте фото или видео в виде файла, связанные с вашей доработкой.\n"
            "Можете отправить несколько файлов подряд.\n\n"
            "Когда закончите, нажмите кнопку 'Готово'",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Готово", callback_data="improvement_files_done")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="improvement_main")]
            ])
        )
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@router.message(ImprovementStates.waiting_for_files)
async def handle_improvement_files(message: Message, state: FSMContext):
    """Обрабатывает файлы доработки"""
    try:
        user_id = message.from_user.id
        
        # Инициализируем временное хранилище для пользователя
        if user_id not in improvement_temp_data:
            improvement_temp_data[user_id] = {
                "file_ids": [],
                "files_info": []
            }
        
        # Обрабатываем разные типы файлов
        if message.photo:
            file_id = message.photo[-1].file_id
            file_type = "фото"
        elif message.video:
            file_id = message.video.file_id
            file_type = "видео"
        elif message.document:
            file_id = message.document.file_id
            file_type = "документ"
        else:
            await message.answer("❌ Поддерживаются только фото, видео и документы!")
            return
        
        # Сохраняем информацию о файле
        improvement_temp_data[user_id]["file_ids"].append(file_id)
        improvement_temp_data[user_id]["files_info"].append({
            "type": file_type,
            "file_id": file_id
        })
        
        await message.answer(
            f"✅ {file_type.capitalize()} добавлен!\n"
            f"Всего файлов: {len(improvement_temp_data[user_id]['file_ids'])}"
        )
        
    except Exception as e:
        await message.answer(f"Ошибка при обработке файла: {str(e)}")

@router.callback_query(F.data == "improvement_files_done")
async def finish_adding_files(callback: CallbackQuery, state: FSMContext):
    """Завершает добавление файлов и показывает предварительный просмотр"""
    try:
        user_id = callback.from_user.id
        data = await state.get_data()
        
        # Получаем временные данные
        temp_data = improvement_temp_data.get(user_id, {})
        file_ids = temp_data.get("file_ids", [])
        files_info = temp_data.get("files_info", [])
        
        improvement_type = data.get("improvement_type")
        title = data.get("title")
        description = data.get("description")
        
        # Формируем текст предварительного просмотра
        type_names = {
            "robot": "робота",
            "code": "кода", 
            "other": "доработки"
        }
        
        preview_text = f"📋 **Предварительный просмотр {type_names.get(improvement_type, 'доработки')}**\n\n"
        if title:
            preview_text += f"🏷️ **Название:** {title}\n"
        preview_text += f"📝 **Описание:** {description}\n\n"
        
        if files_info:
            preview_text += "📎 **Файлы:**\n"
            for i, file_info in enumerate(files_info, 1):
                preview_text += f"{i}. {file_info['type'].capitalize()}\n"
        else:
            preview_text += "📎 **Файлы:** Не добавлены\n"
        
        preview_text += "\nВсё верно? Нажмите 'Подтвердить' для сохранения."
        
        # Показываем клавиатуру подтверждения
        keyboard = get_improvement_confirm_keyboard(improvement_type)
        
        await callback.message.edit_text(
            preview_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data.startswith("improvement_confirm_"))
async def confirm_improvement(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждает и сохраняет доработку"""
    try:
        user_id = callback.from_user.id
        data = await state.get_data()
        
        # Получаем временные данные
        temp_data = improvement_temp_data.get(user_id, {})
        file_ids = temp_data.get("file_ids", [])
        
        improvement_type = data.get("improvement_type")
        title = data.get("title")
        description = data.get("description")
        
        # Получаем информацию о пользователе
        user_query = await session.execute(
            select(User).where(User.tg_id == user_id)
        )
        user_obj = user_query.scalar_one_or_none()
        
        if not user_obj:
            await callback.answer("❌ Пользователь не найден!")
            return
        
        # Создаем новую доработку
        # Сохраняем детальную информацию о файлах (тип + file_id), если она есть
        files_info = improvement_temp_data.get(user_id, {}).get("files_info")
        files_payload = files_info if files_info else (file_ids if file_ids else None)

        new_improvement = Improvement(
            user_tg_id=user_id,
            team_id=user_obj.team_id,
            improvement_type=improvement_type,
            title=title,
            description=description,
            file_ids=files_payload
        )
        
        session.add(new_improvement)
        await session.commit()
        
        # Очищаем временные данные
        if user_id in improvement_temp_data:
            del improvement_temp_data[user_id]
        
        # Очищаем состояние
        await state.clear()
        
        # Показываем сообщение об успехе
        type_names = {
            "robot": "робота",
            "code": "кода",
            "other": "доработки"
        }
        
        await callback.message.edit_text(
            f"✅ **{type_names.get(improvement_type, 'Доработка')} успешно добавлена!**\n\n"
            + (f"🏷️ Название: {title}\n" if title else "")
            + f"📝 Описание: {description}\n"
            + f"📎 Файлов: {len(file_ids) if file_ids else 0}\n\n"
            + "Теперь вы можете просмотреть её в разделе 'Мои доработки'",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Мои доработки", callback_data="improvement_my_list")],
                [InlineKeyboardButton(text="🔧 Главное меню доработок", callback_data="improvement_main")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
        
        await callback.answer("✅ Доработка сохранена!")
        
    except Exception as e:
        await callback.answer(f"Ошибка при сохранении: {str(e)}")

@router.callback_query(F.data == "improvement_my_list")
async def show_my_improvements(callback: CallbackQuery, session: AsyncSession):
    """Показывает список доработок пользователя"""
    try:
        user_id = callback.from_user.id
        
        # Получаем доработки пользователя
        improvements_query = await session.execute(
            select(Improvement)
            .where(Improvement.user_tg_id == user_id)
            .order_by(Improvement.created_at.desc())
        )
        improvements = improvements_query.scalars().all()
        
        if not improvements:
            await callback.message.edit_text(
                "📋 **Мои доработки**\n\n"
                "У вас пока нет добавленных доработок.\n"
                "Добавьте первую доработку!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📸 Добавить фото робота", callback_data="improvement_add_robot")],
                    [InlineKeyboardButton(text="💻 Добавить код", callback_data="improvement_add_code")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="improvement_main")]
                ]),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Показываем список доработок
        keyboard = get_improvement_list_keyboard(improvements)
        
        await callback.message.edit_text(
            f"📋 **Мои доработки**\n\n"
            f"Найдено доработок: {len(improvements)}\n"
            "Выберите доработку для просмотра:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data == "improvement_team_list")
async def show_team_improvements(callback: CallbackQuery, session: AsyncSession):
    """Показывает список доработок команды пользователя"""
    try:
        user_id = callback.from_user.id
        # Получаем пользователя и его команду
        user_q = await session.execute(select(User).where(User.tg_id == user_id))
        user_obj = user_q.scalar_one_or_none()
        if not user_obj or not user_obj.team_id:
            await callback.answer("❌ Сначала привяжите команду в регистрации.")
            return
        # Получаем доработки всей команды
        improvements_query = await session.execute(
            select(Improvement)
            .where(Improvement.team_id == user_obj.team_id)
            .order_by(Improvement.created_at.desc())
        )
        improvements = improvements_query.scalars().all()
        if not improvements:
            await callback.message.edit_text(
                "👥 **Доработки команды**\n\nПока нет доработок в вашей команде.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="improvement_main")]
                ]),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        # Формируем список с указанием автора на кнопках
        buttons = []
        for imp in improvements:
            # Получаем читаемое имя автора
            author_text = None
            try:
                chat = await callback.bot.get_chat(imp.user_tg_id)
                if getattr(chat, 'username', None):
                    author_text = f"@{chat.username}"
                else:
                    author_text = chat.full_name or str(imp.user_tg_id)
            except Exception:
                author_text = str(imp.user_tg_id)

            emoji = "🤖" if imp.improvement_type == "robot" else "💻" if imp.improvement_type == "code" else "📝"
            title_or_desc = imp.title or imp.description or 'Без названия'
            base_text = title_or_desc[:30] + ("..." if len(title_or_desc) > 30 else "")
            text = f"{emoji} {base_text} — от {author_text}"
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"improvement_view_{imp.id}")])

        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="improvement_main")])

        await callback.message.edit_text(
            f"👥 **Доработки команды**\n\nНайдено: {len(improvements)}\nВыберите доработку для просмотра:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data.startswith("improvement_view_"))
async def view_improvement_detail(callback: CallbackQuery, session: AsyncSession):
    """Показывает детали конкретной доработки"""
    try:
        improvement_id = int(callback.data.replace("improvement_view_", ""))
        user_id = callback.from_user.id
        
        # Получаем доработку
        # Разрешаем смотреть доработку владельцу и любому сокоманднику
        improvement_query = await session.execute(
            select(Improvement)
            .join(User, User.team_id == Improvement.team_id, isouter=True)
            .where(Improvement.id == improvement_id)
        )
        improvement = improvement_query.scalar_one_or_none()
        
        if not improvement:
            await callback.answer("❌ Доработка не найдена!")
            return
        # Проверяем право доступа: либо владелец, либо один team_id
        user_q = await session.execute(select(User).where(User.tg_id == user_id))
        me = user_q.scalar_one_or_none()
        if not me or (improvement.user_tg_id != user_id and me.team_id != improvement.team_id):
            await callback.answer("❌ У вас нет доступа к этой доработке")
            return
        
        # Формируем детальную информацию
        type_names = {
            "robot": "робота",
            "code": "кода",
            "other": "доработки"
        }
        
        detail_text = f"🔧 **Детали {type_names.get(improvement.improvement_type, 'доработки')}**\n\n"
        if getattr(improvement, 'title', None):
            detail_text += f"🏷️ Название: {improvement.title}\n"
        detail_text += f"📅 Дата создания: {improvement.created_at.strftime('%d.%m.%Y в %H:%M')}\n"
        
        # Автор (для деталей)
        author_text = None
        try:
            chat = await callback.bot.get_chat(improvement.user_tg_id)
            if getattr(chat, 'username', None):
                author_text = f"@{chat.username}"
            else:
                author_text = chat.full_name or str(improvement.user_tg_id)
        except Exception:
            author_text = str(improvement.user_tg_id)

        detail_text += f"👤 Автор: {author_text}\n"

        if improvement.description:
            detail_text += f"📝 Описание: {improvement.description}\n"
        
        files = improvement.file_ids or []
        if isinstance(files, list) and files:
            detail_text += f"📎 Файлов: {len(files)}\n"
        else:
            detail_text += "📎 Файлов: Нет\n"
        
        # Показываем клавиатуру для работы с доработкой
        keyboard = get_improvement_view_keyboard(improvement.id)
        
        # Если есть вложения, покажем их: для одного вложения отправим его с подписью и кнопками,
        # для нескольких — медиа-группу с подписью на первом элементе и отдельное сообщение с кнопками
        files_to_show = []
        if isinstance(files, list):
            for item in files[:10]:  # ограничим до 10 медиа в группе
                if isinstance(item, dict):
                    ftype = item.get("type")
                    fid = item.get("file_id")
                else:
                    # старый формат: просто file_id -> считаем фото
                    ftype = "фото"
                    fid = item
                if not fid:
                    continue
                if ftype == "фото":
                    files_to_show.append(("photo", fid))
                elif ftype == "видео":
                    files_to_show.append(("video", fid))
                elif ftype == "документ":
                    files_to_show.append(("document", fid))

        try:
            if files_to_show:
                # Сортируем: сначала документы, затем фото, затем видео
                priority = {"document": 0, "photo": 1, "video": 2}
                files_to_show.sort(key=lambda x: priority.get(x[0], 3))

                if len(files_to_show) == 1:
                    mtype, fid = files_to_show[0]
                    if mtype == "photo":
                        await callback.message.answer_photo(photo=fid, caption=detail_text, parse_mode="Markdown", reply_markup=keyboard)
                    elif mtype == "video":
                        await callback.message.answer_video(video=fid, caption=detail_text, parse_mode="Markdown", reply_markup=keyboard)
                    else:
                        await callback.message.answer_document(document=fid, caption=detail_text, parse_mode="Markdown", reply_markup=keyboard)
                    # Удаляем предыдущее сообщение с меню, чтобы не дублировать
                    with contextlib.suppress(Exception):
                        await callback.message.delete()
                else:
                    media_group = []
                    for idx, (mtype, fid) in enumerate(files_to_show):
                        if mtype == "photo":
                            if idx == 0:
                                media_group.append(InputMediaPhoto(media=fid, caption=detail_text, parse_mode="Markdown"))
                            else:
                                media_group.append(InputMediaPhoto(media=fid))
                        elif mtype == "video":
                            if idx == 0:
                                media_group.append(InputMediaVideo(media=fid, caption=detail_text, parse_mode="Markdown"))
                            else:
                                media_group.append(InputMediaVideo(media=fid))
                        else:
                            if idx == 0:
                                media_group.append(InputMediaDocument(media=fid, caption=detail_text, parse_mode="Markdown"))
                            else:
                                media_group.append(InputMediaDocument(media=fid))
                    await callback.message.answer_media_group(media_group)
                    # Отдельно отправляем клавиатуру управления
                    await callback.message.answer("Выберите действие:", reply_markup=keyboard)
                    with contextlib.suppress(Exception):
                        await callback.message.delete()
            else:
                # Вложений нет — просто обновляем текст и клавиатуру
                await callback.message.edit_text(
                    detail_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        except Exception:
            # Если не удалось отправить медиа, fallback — только текст
            await callback.message.edit_text(
                detail_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data.startswith("improvement_delete_"))
async def delete_improvement(callback: CallbackQuery, session: AsyncSession):
    """Удаляет доработку"""
    try:
        improvement_id = int(callback.data.replace("improvement_delete_", ""))
        user_id = callback.from_user.id
        
        # Удаляем доработку
        delete_query = await session.execute(
            select(Improvement).where(
                Improvement.id == improvement_id,
                Improvement.user_tg_id == user_id
            )
        )
        improvement = delete_query.scalar_one_or_none()
        
        if not improvement:
            await callback.answer("❌ Доработка не найдена!")
            return
        
        await session.delete(improvement)
        await session.commit()
        
        await callback.answer("🗑️ Доработка удалена!")
        
        # Возвращаемся к списку доработок
        await show_my_improvements(callback, session)
        
    except Exception as e:
        await callback.answer(f"Ошибка при удалении: {str(e)}")

@router.callback_query(F.data.regexp(r"^improvement_edit_\d+$"))
async def edit_improvement_menu(callback: CallbackQuery):
    """Показывает меню редактирования доработки"""
    try:
        improvement_id = int(callback.data.replace("improvement_edit_", ""))
        
        keyboard = get_improvement_edit_keyboard(improvement_id)

        text = (
            "✏️ **Редактирование доработки**\n\n"
            "Выберите, что хотите изменить:"
        )

        # Сообщение-источник может быть медиа с подписью, поэтому делаем безопасный fallback
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception:
            try:
                await callback.message.edit_caption(text, reply_markup=keyboard, parse_mode="Markdown")
            except Exception:
                await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data.startswith("improvement_add_files_"))
async def start_add_files_to_improvement(callback: CallbackQuery, state: FSMContext):
    """Начинает добавление новых файлов к существующей доработке"""
    try:
        improvement_id = int(callback.data.replace("improvement_add_files_", ""))
        await state.update_data(editing_improvement_id=improvement_id)
        await state.set_state(ImprovementStates.waiting_for_edit_files)

        prompt_text = (
            "📸 **Добавление файлов**\n\n"
            "Отправьте фото, видео или документы, которые хотите прикрепить к доработке.\n\n"
            "Когда закончите, нажмите 'Готово'"
        )
        prompt_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="improvement_edit_files_done")],
            [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"improvement_view_{improvement_id}")]
        ])

        try:
            await callback.message.edit_text(prompt_text, reply_markup=prompt_kb, parse_mode="Markdown")
        except Exception:
            try:
                await callback.message.edit_caption(prompt_text, reply_markup=prompt_kb, parse_mode="Markdown")
            except Exception:
                await callback.message.answer(prompt_text, reply_markup=prompt_kb, parse_mode="Markdown")
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.message(ImprovementStates.waiting_for_edit_files)
async def handle_add_files_to_improvement(message: Message, state: FSMContext):
    """Копит новые файлы для добавления к существующей доработке"""
    try:
        data = await state.get_data()
        bucket = data.get("edit_files_bucket") or []

        if message.photo:
            fid = message.photo[-1].file_id
            bucket.append({"type": "фото", "file_id": fid})
        elif message.video:
            fid = message.video.file_id
            bucket.append({"type": "видео", "file_id": fid})
        elif message.document:
            fid = message.document.file_id
            bucket.append({"type": "документ", "file_id": fid})
        else:
            await message.answer("❌ Поддерживаются только фото, видео и документы!")
            return

        await state.update_data(edit_files_bucket=bucket)
        await message.answer(f"✅ Файл добавлен! Всего новых файлов: {len(bucket)}")
    except Exception as e:
        await message.answer(f"Ошибка при добавлении файла: {str(e)}")

@router.callback_query(F.data == "improvement_edit_files_done")
async def finish_add_files_to_improvement(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Сохраняет добавленные файлы в БД"""
    try:
        data = await state.get_data()
        improvement_id = data.get("editing_improvement_id")
        new_files = data.get("edit_files_bucket") or []

        if not improvement_id:
            await callback.answer("❌ Не найдена доработка")
            return

        # Загружаем текущую доработку
        imp_q = await session.execute(
            select(Improvement).where(Improvement.id == improvement_id)
        )
        imp = imp_q.scalar_one_or_none()
        if not imp:
            await callback.answer("❌ Доработка не найдена")
            return

        # Приводим существующие файлы к единому формату [{type,file_id}]
        existing = []
        if isinstance(imp.file_ids, list):
            for item in imp.file_ids:
                if isinstance(item, dict):
                    if item.get("file_id"):
                        existing.append({"type": item.get("type", "фото"), "file_id": item.get("file_id")})
                else:
                    existing.append({"type": "фото", "file_id": item})

        updated_files = existing + new_files

        await session.execute(
            update(Improvement)
            .where(Improvement.id == improvement_id)
            .values(file_ids=updated_files, updated_at=datetime.now())
        )
        await session.commit()

        # Очистка состояния
        await state.update_data(edit_files_bucket=[])
        await state.set_state(None)

        success_text = "✅ Файлы добавлены к доработке!"
        success_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 К доработке", callback_data=f"improvement_view_{improvement_id}")],
            [InlineKeyboardButton(text="📋 К списку", callback_data="improvement_my_list")]
        ])

        try:
            await callback.message.edit_text(success_text, reply_markup=success_kb)
        except Exception:
            try:
                await callback.message.edit_caption(success_text, reply_markup=success_kb)
            except Exception:
                await callback.message.answer(success_text, reply_markup=success_kb)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка при сохранении: {str(e)}")

@router.callback_query(F.data.startswith("improvement_remove_files_"))
async def remove_all_files_from_improvement(callback: CallbackQuery, session: AsyncSession):
    """Удаляет все файлы у доработки"""
    try:
        improvement_id = int(callback.data.replace("improvement_remove_files_", ""))
        # Обнуляем файлы
        await session.execute(
            update(Improvement)
            .where(Improvement.id == improvement_id)
            .values(file_ids=None, updated_at=datetime.now())
        )
        await session.commit()
        await callback.answer("🗑️ Все файлы удалены")
        await show_my_improvements(callback, session)
    except Exception as e:
        await callback.answer(f"Ошибка при удалении файлов: {str(e)}")
@router.callback_query(F.data.startswith("improvement_edit_desc_"))
async def start_edit_description(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование описания"""
    try:
        improvement_id = int(callback.data.replace("improvement_edit_desc_", ""))
        
        # Сохраняем ID доработки в состоянии
        await state.update_data(editing_improvement_id=improvement_id)
        await state.set_state(ImprovementStates.waiting_for_edit_description)
        
        prompt_text = (
            "📝 **Изменение описания**\n\n"
            "Отправьте новое описание для вашей доработки:"
        )
        prompt_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"improvement_view_{improvement_id}")]
        ])

        # Сообщение с деталями могло быть медиа с подписью — тогда edit_text упадёт.
        # Делаем безопасную последовательность: edit_text -> edit_caption -> answer
        try:
            await callback.message.edit_text(prompt_text, reply_markup=prompt_kb, parse_mode="Markdown")
        except Exception:
            try:
                await callback.message.edit_caption(prompt_text, reply_markup=prompt_kb, parse_mode="Markdown")
            except Exception:
                await callback.message.answer(prompt_text, reply_markup=prompt_kb, parse_mode="Markdown")
        
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.message(ImprovementStates.waiting_for_edit_description)
async def handle_edit_description(message: Message, state: FSMContext, session: AsyncSession):
    """Обрабатывает новое описание"""
    try:
        new_description = message.text
        data = await state.get_data()
        improvement_id = data.get("editing_improvement_id")
        
        # Обновляем описание в базе данных
        await session.execute(
            update(Improvement)
            .where(Improvement.id == improvement_id)
            .values(
                description=new_description,
                updated_at=datetime.now()
            )
        )
        await session.commit()
        
        # Очищаем состояние
        await state.clear()
        
        await message.answer(
            "✅ **Описание обновлено!**\n\n"
            f"Новое описание: {new_description}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 К доработке", callback_data=f"improvement_view_{improvement_id}")],
                [InlineKeyboardButton(text="📋 К списку", callback_data="improvement_my_list")]
            ])
        )
        
    except Exception as e:
        await message.answer(f"Ошибка при обновлении: {str(e)}")
