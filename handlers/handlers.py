from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserTeams
from calculator import fll_calculator
from sqlalchemy import select
from datetime import datetime
from database.models import FLLResult, User
from aiogram import types
from local_storage import local_storage



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



@router.callback_query(F.data == "calc_save")
async def show_save_options(callback: CallbackQuery):
    """Показывает опции сохранения результатов"""
    try:
        user_id = callback.from_user.id
        total_score = fll_calculator.get_total_score(user_id)
        
        if total_score == 0:
            await callback.answer("❌ Нет результатов для сохранения! Сначала наберите очки.")
            return
        
        keyboard = fll_calculator.get_save_keyboard()
        await callback.message.edit_text(
            f"💾 **Сохранение результатов**\n\n"
            f"🎯 Общий счет: {total_score}\n"
            f"📊 Максимально возможный: {fll_calculator.get_max_possible_score()}\n\n"
            f"Хотите сохранить эти результаты?",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data == "calc_save_simple")
async def save_results(callback: CallbackQuery):
    """Сохраняет результаты локально"""
    try:
        user_id = callback.from_user.id
        total_score = fll_calculator.get_total_score(user_id)
        
        if total_score == 0:
            await callback.answer("❌ Нет результатов для сохранения!")
            return
        
        # Создаем новый результат с текущей датой и временем
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime('%d.%m.%Y в %H:%M')
        
        # Сохраняем результат локально
        new_result = local_storage.save_result(
            user_id=user_id,
            mission_scores=fll_calculator.get_user_scores_dict(user_id),
            total_score=total_score,
            max_possible_score=fll_calculator.get_max_possible_score(),
            name=f"Результат от {formatted_datetime}"
        )
        
        # Возвращаемся к калькулятору
        keyboard = fll_calculator.get_main_keyboard(user_id)
        await callback.message.edit_text(
            "🧮 **Калькулятор миссий FLL - Богатый урожай**\n\n"
            f"✅ Результаты успешно сохранены!\n"
            f"📅 Дата: {formatted_datetime}\n"
            "Выберите миссию для установки очков:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer("✅ Результаты сохранены!")
        
    except Exception as e:
        await callback.answer(f"Ошибка при сохранении: {str(e)}")





@router.callback_query(F.data == "calc_my_results")
async def show_my_results(callback: CallbackQuery):
    """Показывает сохраненные результаты пользователя"""
    try:
        user_id = callback.from_user.id
        
        # Получаем результаты пользователя из локального хранилища
        results = local_storage.get_user_results(user_id)
        
        # Сортируем по дате создания (новые сначала)
        results.sort(key=lambda x: x.created_at, reverse=True)
        
        if not results:
            keyboard = fll_calculator.get_main_keyboard(user_id)
            await callback.message.edit_text(
                "🧮 **Калькулятор миссий FLL - Богатый урожай**\n\n"
                "📋 У вас пока нет сохраненных результатов.\n"
                "Выберите миссию для установки очков:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback.answer("📋 Нет сохраненных результатов")
            return
        
        keyboard = fll_calculator.get_results_keyboard(results)
        await callback.message.edit_text(
            "📋 **Мои сохраненные результаты**\n\n"
            f"Найдено результатов: {len(results)}\n"
            "Выберите результат для просмотра:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("calc_view_result_"))
async def view_result_detail(callback: CallbackQuery):
    """Показывает детали конкретного результата"""
    try:
        result_id = int(callback.data.replace("calc_view_result_", ""))
        user_id = callback.from_user.id
        
        # Получаем результат из локального хранилища
        result = local_storage.get_result_by_id(user_id, result_id)
        
        if not result:
            await callback.answer("❌ Результат не найден!")
            return
        
        # Формируем детальную информацию с улучшенным отображением даты
        created_at = datetime.fromisoformat(result.created_at)
        detail_text = f"📊 **Детали результата**\n\n"
        detail_text += f"📅 Дата и время: {created_at.strftime('%d.%m.%Y в %H:%M')}\n"
        detail_text += f"🎯 Общий счет: {result.total_score}/{result.max_possible_score}\n"
        detail_text += f"📈 Процент выполнения: {(result.total_score / result.max_possible_score * 100):.1f}%\n\n"
        
        detail_text += "🏆 **Разбивка по миссиям:**\n"
        for mission_id, score in result.mission_scores.items():
            mission_name = fll_calculator.missions.get(mission_id, {}).get('name', mission_id)
            max_points = fll_calculator.missions.get(mission_id, {}).get('max_points', 0)
            detail_text += f"• {mission_name}: {score}/{max_points}\n"
        
        keyboard = fll_calculator.get_result_detail_keyboard(result_id)
        await callback.message.edit_text(
            detail_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("calc_delete_result_"))
async def delete_result(callback: CallbackQuery):
    """Удаляет сохраненный результат"""
    try:
        result_id = int(callback.data.replace("calc_delete_result_", ""))
        user_id = callback.from_user.id
        
        # Удаляем результат из локального хранилища
        success = local_storage.delete_result(user_id, result_id)
        
        if not success:
            await callback.answer("❌ Результат не найден!")
            return
        
        await callback.answer("🗑️ Результат удален!")
        
        # Возвращаемся к списку результатов
        await show_my_results(callback)
        
    except Exception as e:
        await callback.answer(f"Ошибка при удалении: {str(e)}")


@router.callback_query(F.data == "calc_view_report")
async def show_report_choice(callback: CallbackQuery):
    """Показывает выбор типа отчёта"""
    try:
        keyboard = fll_calculator.get_report_choice_keyboard()
        await callback.message.edit_text(
            "📊 **Выберите тип отчёта**\n\n"
            "📋 **Краткий отчёт** - статистика в текстовом виде\n"
            "📊 **Детальный отчёт** - полная информация в Excel файле",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data == "calc_brief_report")
async def show_brief_report_period(callback: CallbackQuery):
    """Показывает выбор периода для краткого отчёта"""
    try:
        keyboard = fll_calculator.get_report_period_keyboard("brief_report")
        await callback.message.edit_text(
            "📋 **Выберите период для краткого отчёта**\n\n"
            "Выберите временной период для анализа ваших результатов:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data == "calc_detailed_report")
async def show_detailed_report_period(callback: CallbackQuery):
    """Показывает выбор периода для детального отчёта"""
    try:
        keyboard = fll_calculator.get_report_period_keyboard("detailed_report")
        await callback.message.edit_text(
            "📊 **Выберите период для детального отчёта**\n\n"
            "Выберите временной период для создания Excel отчёта:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("calc_brief_report_"))
async def generate_brief_report_with_period(callback: CallbackQuery):
    """Генерирует краткий отчёт с фильтрацией по периоду"""
    try:
        user_id = callback.from_user.id
        period = callback.data.replace("calc_brief_report_", "")
        
        # Определяем дату начала периода
        from datetime import timedelta
        now = datetime.now()
        
        if period == "week":
            start_date = now - timedelta(days=7)
            period_name = "неделю"
        elif period == "month":
            start_date = now - timedelta(days=30)
            period_name = "месяц"
        elif period == "half_year":
            start_date = now - timedelta(days=180)
            period_name = "полгода"
        elif period == "year":
            start_date = now - timedelta(days=365)
            period_name = "год"
        elif period == "all":
            start_date = None
            period_name = "всё время"
        else:
            await callback.answer("❌ Неверный период!")
            return
        
        # Получаем результаты пользователя с фильтрацией по дате
        results = local_storage.get_results_by_period(user_id, start_date)
        
        # Сортируем по дате создания (новые сначала)
        results.sort(key=lambda x: x.created_at, reverse=True)
        
        if not results:
            back_button = [InlineKeyboardButton(text="◀️ Назад к выбору периода", callback_data="calc_brief_report")]
            keyboard = InlineKeyboardMarkup(inline_keyboard=[back_button])
            await callback.message.edit_text(
                f"📋 **Краткий отчёт за {period_name}**\n\n"
                f"За выбранный период нет сохранённых результатов.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Генерируем краткий отчёт
        report_text = fll_calculator.generate_brief_report(results)
        report_text = f"📋 **Краткий отчёт за {period_name}**\n\n" + report_text
        
        # Создаём клавиатуру для возврата
        back_button = [InlineKeyboardButton(text="◀️ Назад к результатам", callback_data="calc_my_results")]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[back_button])
        
        await callback.message.edit_text(
            report_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка при генерации отчёта: {str(e)}")


@router.callback_query(F.data.startswith("calc_detailed_report_"))
async def generate_detailed_report_with_period(callback: CallbackQuery):
    """Генерирует детальный Excel отчёт с фильтрацией по периоду"""
    try:
        user_id = callback.from_user.id
        period = callback.data.replace("calc_detailed_report_", "")
        
        # Определяем дату начала периода
        from datetime import timedelta
        now = datetime.now()
        
        if period == "week":
            start_date = now - timedelta(days=7)
            period_name = "неделю"
        elif period == "month":
            start_date = now - timedelta(days=30)
            period_name = "месяц"
        elif period == "half_year":
            start_date = now - timedelta(days=180)
            period_name = "полгода"
        elif period == "year":
            start_date = now - timedelta(days=365)
            period_name = "год"
        elif period == "all":
            start_date = None
            period_name = "всё время"
        else:
            await callback.answer("❌ Неверный период!")
            return
        
        # Получаем результаты пользователя с фильтрацией по дате
        results = local_storage.get_results_by_period(user_id, start_date)
        
        # Сортируем по дате создания (новые сначала)
        results.sort(key=lambda x: x.created_at, reverse=True)
        
        if not results:
            await callback.answer(f"❌ Нет результатов за {period_name} для создания отчёта!")
            return
        
        # Генерируем Excel отчёт
        excel_file = fll_calculator.generate_detailed_excel_report(results)
        
        if excel_file is None:
            await callback.answer("❌ Ошибка при создании отчёта!")
            return
        
        # Создаём имя файла с периодом и текущей датой
        current_date = datetime.now().strftime('%Y-%m-%d_%H-%M')
        period_suffix = {
            "week": "неделя",
            "month": "месяц", 
            "half_year": "полгода",
            "year": "год",
            "all": "все_время"
        }.get(period, period)
        filename = f"FLL_отчёт_{period_suffix}_{current_date}.xlsx"
        
        # Отправляем файл
        await callback.message.answer_document(
            document=types.BufferedInputFile(
                excel_file.getvalue(),
                filename=filename
            ),
            caption=f"📊 **Детальный отчёт FLL за {period_name}**\n\n"
                   "Файл содержит:\n"
                   "• Общую статистику\n"
                   "• Разбивку по миссиям\n"
                   "• Сводку по миссиям"
        )
        
        await callback.answer("✅ Отчёт отправлен!")
        
    except Exception as e:
        await callback.answer(f"Ошибка при создании отчёта: {str(e)}")






