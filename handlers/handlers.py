from aiogram import Router, F
from aiogram.types import CallbackQuery
from calculator import fll_calculator


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
