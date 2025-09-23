from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import pandas as pd
from io import BytesIO
from datetime import datetime
import json


class FLLCalculator:
    def __init__(self):
        # Глобальный максимум сезона (итог должен быть 700)
        self.global_max_total = 700
        self.missions = {
            "mission_1": {"name": "Проверка оборудования", "max_points": 40},
            "mission_2": {"name": "Инновационный проект", "max_points": 30},
            "mission_3": {"name": "Светофор", "max_points": 30},
            "mission_4": {"name": "Надземный пешеходный переход", "max_points": 30},
            "mission_5": {"name": "Ямочный ремонт", "max_points": 25},
            "mission_6": {"name": "Самокаты", "max_points": 20},
            "mission_7": {"name": "Парковка самокатов", "max_points": 80},
            "mission_8": {"name": "Железнодорожный переезд", "max_points": 45},
            "mission_9": {"name": "Лежачий полицейский", "max_points": 25},
            "mission_10": {"name": "Эвакуатор", "max_points": 50},
            "mission_11": {"name": "Дорожное ограждение", "max_points": 25},
            "mission_12": {"name": "Автобус", "max_points": 30},
            "mission_13": {"name": 'Знак"СТОП!"', "max_points": 35},
            "mission_14": {"name": "Автобусная остановка", "max_points": 40},
            "mission_15": {"name": "Парковка", "max_points": 50},
            "mission_16": {"name": "Взаимодействие", "max_points": 40},
            "mission_17": {"name": "Жетоны точности", "max_points": 60},
        }
        # Наборы пользовательских кнопок для отдельных миссий.
        # Пример: для проверки оборудования показываем только 0/30/40
        # Чтобы настроить другие миссии, добавьте сюда: "mission_X": [список баллов]
        self.mission_point_presets = {
            "mission_1": [0, 30, 40],
            "mission_2": [0, 20, 30],
            "mission_3": [0, 15, 30],
            "mission_4": [0, 20, 30],
            "mission_5": [0, 25],
            "mission_8": [0, 25, 45],
            "mission_9": [0, 25],
            "mission_10": [0, 10, 50],
            "mission_11": [0, 25],
            "mission_12": [0, 10, 30],
            "mission_13": [0, 35],
            "mission_14": [0, 20, 40],
            "mission_15": [0, 20, 30, 50],
            "mission_16": [0, 40],
            "mission_17": [0, 15, 25, 35, 35, 60],
        }
        # Правила миссий, где нужно вводить/выбирать количество
        # Используем отображение количества в баллы через коэффициент, при этом
        # под капотом формируем стандартные callback с конкретным числом баллов.
        self.count_mission_rules = {
            # Самокаты: 10 баллов за каждый; максимум 2 шт = 20 баллов
            "mission_6": {"points_per_unit": 10, "max_units": 2, "unit_label": "шт"},
            # Парковка самокатов: 20 баллов за каждый; максимум 4 шт = 80 баллов
            "mission_7": {"points_per_unit": 20, "max_units": 4, "unit_label": "шт"},
        }
        self.user_scores = {}
    
    def get_main_keyboard(self, user_id=None):
        """Главная клавиатура калькулятора"""
        buttons = []
        
        for mission_id, mission_data in self.missions.items():
            current_score = self.get_mission_score(user_id, mission_id) if user_id else 0
            button = InlineKeyboardButton(
                text=f"{mission_data['name']} ({current_score}/{mission_data['max_points']})",
                callback_data=f"calc_{mission_id}"
            )
            buttons.append([button])
        
        # Кнопки управления
        total_score = self.get_total_score(user_id) if user_id else 0
        max_total = self.get_max_possible_score()
        
        control_buttons = [
            InlineKeyboardButton(text=f"📊 Итого: {total_score}/{max_total}", callback_data="calc_total"),
            InlineKeyboardButton(text="🔄 Сбросить", callback_data="calc_reset")
        ]
        buttons.append(control_buttons)
        
        # Новые кнопки для сохранения и просмотра результатов
        save_results_button = [InlineKeyboardButton(text="💾 Сохранить результаты", callback_data="calc_save")]
        my_results_button = [InlineKeyboardButton(text="📋 Мои результаты", callback_data="calc_my_results")]
        buttons.append(save_results_button)
        buttons.append(my_results_button)
        
        # Изменяем callback_data для кнопки "Назад"
        back_button = [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu")]
        buttons.append(back_button)
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def get_mission_keyboard(self, mission_id):
        """Клавиатура для конкретной миссии"""
        if mission_id not in self.missions:
            return None
            
        mission = self.missions[mission_id]
        max_points = mission["max_points"]
        
        buttons = []
        current_row = []
        
        # 1) Пользовательские пресеты баллов — если заданы, используем их
        if mission_id in self.mission_point_presets:
            for points in self.mission_point_presets[mission_id]:
                # гарантируем, что не превышаем максимум миссии
                safe_points = min(points, max_points)
                button = InlineKeyboardButton(
                    text=str(points),
                    callback_data=f"calc_set_{mission_id}_{safe_points}"
                )
                current_row.append(button)
                if len(current_row) == 3:  # 3 кнопки в ряд более удобно для кастомных наборов
                    buttons.append(current_row)
                    current_row = []
        # 2) Особые миссии: выбор количества (конвертируем количество в баллы)
        elif mission_id in self.count_mission_rules:
            rule = self.count_mission_rules[mission_id]
            ppu = rule["points_per_unit"]
            max_units = rule["max_units"]
            unit_label = rule.get("unit_label", "шт")

            for count in range(0, max_units + 1):
                points = count * ppu
                button = InlineKeyboardButton(
                    text=f"{count} {unit_label} ({points})",
                    callback_data=f"calc_set_{mission_id}_{points}"
                )
                current_row.append(button)
                if len(current_row) == 3:  # 3 кнопки в ряд для компактности
                    buttons.append(current_row)
                    current_row = []
        else:
            # Создаем кнопки с очками (по 5 очков)
            for points in range(0, max_points + 1, 5):
                if points <= max_points:
                    button = InlineKeyboardButton(
                        text=str(points),
                        callback_data=f"calc_set_{mission_id}_{points}"
                    )
                    current_row.append(button)
                    
                    if len(current_row) == 4:  # 4 кнопки в ряд
                        buttons.append(current_row)
                        current_row = []
        
        # Добавляем оставшиеся кнопки
        if current_row:
            buttons.append(current_row)
        
        if mission_id not in self.count_mission_rules and mission_id not in self.mission_point_presets:
            # Добавляем максимальное значение, если его нет в списке (для обычных миссий)
            if max_points % 5 != 0:
                max_button = InlineKeyboardButton(
                    text=str(max_points),
                    callback_data=f"calc_set_{mission_id}_{max_points}"
                )
                buttons.append([max_button])
        
        # Кнопка назад
        back_button = InlineKeyboardButton(text="◀️ Назад к миссиям", callback_data="calc_back")
        buttons.append([back_button])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def get_save_keyboard(self):
        """Клавиатура для сохранения результатов"""
        buttons = [
            [InlineKeyboardButton(text="💾 Сохранить результат", callback_data="calc_save_simple")],
            [InlineKeyboardButton(text="◀️ Назад к калькулятору", callback_data="calc_back")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    

    
    def get_results_keyboard(self, results):
        """Клавиатура для просмотра результатов"""
        buttons = []
        
        # Добавляем кнопку для просмотра отчёта
        if results:
            report_button = [InlineKeyboardButton(text="📊 Посмотреть отчёт", callback_data="calc_view_report")]
            buttons.append(report_button)
        
        for result in results:
            # Используем сохраненное имя или создаем из даты
            if result.name:
                name = result.name
            else:
                name = f"Результат от {result.created_at.strftime('%d.%m.%Y в %H:%M')}"
            
            button_text = f"{name} ({result.total_score}/{result.max_possible_score})"
            button = InlineKeyboardButton(
                text=button_text,
                callback_data=f"calc_view_result_{result.id}"
            )
            buttons.append([button])
        
        # Кнопка назад
        back_button = [InlineKeyboardButton(text="◀️ Назад к калькулятору", callback_data="calc_back")]
        buttons.append(back_button)
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def get_report_choice_keyboard(self):
        """Клавиатура для выбора типа отчёта"""
        buttons = [
            [InlineKeyboardButton(text="📋 Краткий отчёт", callback_data="calc_brief_report")],
            [InlineKeyboardButton(text="📊 Детальный отчёт (Excel)", callback_data="calc_detailed_report")],
            [InlineKeyboardButton(text="◀️ Назад к результатам", callback_data="calc_my_results")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def get_report_period_keyboard(self, report_type):
        """Клавиатура для выбора периода отчёта"""
        buttons = [
            [InlineKeyboardButton(text="📅 За неделю", callback_data=f"calc_{report_type}_week")],
            [InlineKeyboardButton(text="📅 За месяц", callback_data=f"calc_{report_type}_month")],
            [InlineKeyboardButton(text="📅 За полгода", callback_data=f"calc_{report_type}_half_year")],
            [InlineKeyboardButton(text="📅 За год", callback_data=f"calc_{report_type}_year")],
            [InlineKeyboardButton(text="📅 За всё время", callback_data=f"calc_{report_type}_all")],
            [InlineKeyboardButton(text="◀️ Назад к выбору отчёта", callback_data="calc_view_report")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def get_result_detail_keyboard(self, result_id):
        """Клавиатура для детального просмотра результата"""
        buttons = [
            [InlineKeyboardButton(text="🗑️ Удалить результат", callback_data=f"calc_delete_result_{result_id}")],
            [InlineKeyboardButton(text="◀️ Назад к результатам", callback_data="calc_my_results")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def set_mission_score(self, user_id, mission_id, score):
        """Устанавливает очки за миссию"""
        if not user_id or mission_id not in self.missions:
            return False
            
        if user_id not in self.user_scores:
            self.user_scores[user_id] = {}
        
        max_points = self.missions[mission_id]["max_points"]
        if 0 <= score <= max_points:
            self.user_scores[user_id][mission_id] = score
            return True
        return False
    
    def get_mission_score(self, user_id, mission_id):
        """Получает очки за миссию"""
        if (user_id and 
            user_id in self.user_scores and 
            mission_id in self.user_scores[user_id]):
            return self.user_scores[user_id][mission_id]
        return 0
    
    def get_total_score(self, user_id):
        """Вычисляет общий счет"""
        if not user_id or user_id not in self.user_scores:
            return 0
        return sum(self.user_scores[user_id].values())
    
    def reset_scores(self, user_id):
        """Сбрасывает все очки пользователя"""
        if user_id and user_id in self.user_scores:
            self.user_scores[user_id] = {}
    
    def get_score_breakdown(self, user_id):
        """Возвращает детальную разбивку очков"""
        if not user_id or user_id not in self.user_scores:
            breakdown = "🏆 **Детальная разбивка очков:**\n\n"
            for mission_id, mission_data in self.missions.items():
                breakdown += f"⭕ {mission_data['name']}: 0/{mission_data['max_points']}\n"
            
            max_total = self.get_max_possible_score()
            breakdown += f"\n🎯 **Общий счет: 0/{max_total}**"
            breakdown += f"\n📈 **Процент выполнения: 0.0%**"
            return breakdown
        
        breakdown = "🏆 **Детальная разбивка очков:**\n\n"
        total = 0
        
        for mission_id, mission_data in self.missions.items():
            score = self.get_mission_score(user_id, mission_id)
            total += score
            status = "✅" if score > 0 else "⭕"
            breakdown += f"{status} {mission_data['name']}: {score}/{mission_data['max_points']}\n"
        
        max_total = self.get_max_possible_score()
        breakdown += f"\n🎯 **Общий счет: {total}/{max_total}**"
        
        # Добавляем процент выполнения
        percentage = (total / max_total) * 100 if max_total > 0 else 0
        breakdown += f"\n📈 **Процент выполнения: {percentage:.1f}%**"
        
        return breakdown
    
    def get_user_scores_dict(self, user_id):
        """Возвращает словарь с очками пользователя для сохранения"""
        if not user_id or user_id not in self.user_scores:
            return {}
        return self.user_scores[user_id].copy()
    
    def get_max_possible_score(self):
        """Возвращает максимально возможный счет"""
        # Если задан глобальный максимум сезона — возвращаем его
        if getattr(self, "global_max_total", None):
            return self.global_max_total
        return sum(mission["max_points"] for mission in self.missions.values())
    
    def generate_brief_report(self, results):
        """Генерирует краткий отчёт в виде текста"""
        if not results:
            return "📋 **Краткий отчёт**\n\nНет сохранённых результатов для отчёта."
        
        report = "📊 **Общая статистика:**\n"
        report += f"• Всего результатов: {len(results)}\n"
        
        # Подсчитываем статистику
        total_scores = [r.total_score for r in results]
        avg_score = sum(total_scores) / len(total_scores) if total_scores else 0
        max_score = max(total_scores) if total_scores else 0
        min_score = min(total_scores) if total_scores else 0
        
        report += f"• Средний балл: {avg_score:.1f}\n"
        report += f"• Максимальный балл: {max_score}\n"
        report += f"• Минимальный балл: {min_score}\n\n"
        
        # Анализ прогресса
        if len(results) > 1:
            first_result = results[-1]  # Самый старый результат
            last_result = results[0]    # Самый новый результат
            
            progress = last_result.total_score - first_result.total_score
            progress_text = "📈" if progress > 0 else "📉" if progress < 0 else "➡️"
            report += f"{progress_text} **Прогресс:** {progress:+d} баллов\n\n"
        
        # Последние 5 результатов
        recent_results = results[:5]
        report += f"📅 **Последние результаты:**\n"
        for i, result in enumerate(recent_results, 1):
            # Обрабатываем как строку ISO, так и объект datetime
            if hasattr(result.created_at, 'strftime'):
                date_str = result.created_at.strftime('%d.%m.%Y')
            else:
                # Если это строка ISO, преобразуем в datetime
                from datetime import datetime
                created_at = datetime.fromisoformat(result.created_at)
                date_str = created_at.strftime('%d.%m.%Y')
            
            percentage = (result.total_score / result.max_possible_score * 100) if result.max_possible_score > 0 else 0
            report += f"{i}. {date_str}: {result.total_score}/{result.max_possible_score} ({percentage:.1f}%)\n"
        
        return report
    
    def generate_detailed_excel_report(self, results):
        """Генерирует детальный отчёт в формате Excel"""
        if not results:
            return None
        
        # Создаём Excel файл в памяти
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: Общая статистика
            stats_data = []
            for result in results:
                # Обрабатываем как строку ISO, так и объект datetime
                if hasattr(result.created_at, 'strftime'):
                    date_str = result.created_at.strftime('%d.%m.%Y %H:%M')
                else:
                    # Если это строка ISO, преобразуем в datetime
                    from datetime import datetime
                    created_at = datetime.fromisoformat(result.created_at)
                    date_str = created_at.strftime('%d.%m.%Y %H:%M')
                
                percentage = (result.total_score / result.max_possible_score * 100) if result.max_possible_score > 0 else 0
                stats_data.append({
                    'Дата': date_str,
                    'Общий балл': result.total_score,
                    'Максимальный балл': result.max_possible_score,
                    'Процент выполнения': f"{percentage:.1f}%",
                    'Название': result.name or f"Результат от {date_str}"
                })
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Общая статистика', index=False)
            
            # Добавляем расширенную сводку по результатам (лист 'Сводка')
            if results:
                summary_rows = []
                for result in results:
                    # Дата
                    if hasattr(result.created_at, 'strftime'):
                        date_str = result.created_at.strftime('%d.%m.%Y %H:%M')
                    else:
                        from datetime import datetime
                        created_at = datetime.fromisoformat(result.created_at)
                        date_str = created_at.strftime('%d.%m.%Y %H:%M')
                    # Количество выполненных миссий
                    done_missions = [
                        self.missions.get(m_id, {}).get('name', m_id)
                        for m_id, score in result.mission_scores.items() if score > 0
                    ]
                    num_done = len(done_missions)
                    done_str = ', '.join(done_missions) if done_missions else '-'
                    percentage = (result.total_score / result.max_possible_score * 100) if result.max_possible_score > 0 else 0
                    summary_rows.append({
                        'Дата': date_str,
                        'Общий балл': result.total_score,
                        'Выполнено миссий': num_done,
                        'Список выполненных миссий': done_str,
                        'Максимальный балл': result.max_possible_score,
                        'Процент выполнения': f"{percentage:.1f}%"
                    })
                summary_df = pd.DataFrame(summary_rows)
                summary_df.to_excel(writer, sheet_name='Сводка', index=False)
            
            # Лист 2: Детальная разбивка по миссиям
            missions_data = []
            for result in results:
                # Обрабатываем как строку ISO, так и объект datetime
                if hasattr(result.created_at, 'strftime'):
                    date_str = result.created_at.strftime('%d.%m.%Y %H:%M')
                else:
                    # Если это строка ISO, преобразуем в datetime
                    from datetime import datetime
                    created_at = datetime.fromisoformat(result.created_at)
                    date_str = created_at.strftime('%d.%m.%Y %H:%M')
                
                for mission_id, score in result.mission_scores.items():
                    mission_name = self.missions.get(mission_id, {}).get('name', mission_id)
                    max_points = self.missions.get(mission_id, {}).get('max_points', 0)
                    missions_data.append({
                        'Дата': date_str,
                        'Миссия': mission_name,
                        'Балл': score,
                        'Максимум': max_points,
                        'Процент': f"{(score / max_points * 100):.1f}%" if max_points > 0 else "0%"
                    })
            
            missions_df = pd.DataFrame(missions_data)
            missions_df.to_excel(writer, sheet_name='Разбивка по миссиям', index=False)
            
            # Лист 3: Сводная таблица по миссиям
            pivot_data = []
            for mission_id, mission_data in self.missions.items():
                mission_name = mission_data['name']
                max_points = mission_data['max_points']
                
                # Собираем все баллы за эту миссию
                mission_scores = []
                for result in results:
                    if mission_id in result.mission_scores:
                        mission_scores.append(result.mission_scores[mission_id])
                
                if mission_scores:
                    avg_score = sum(mission_scores) / len(mission_scores)
                    max_score = max(mission_scores)
                    min_score = min(mission_scores)
                else:
                    avg_score = max_score = min_score = 0
                
                pivot_data.append({
                    'Миссия': mission_name,
                    'Максимальный балл': max_points,
                    'Средний балл': f"{avg_score:.1f}",
                    'Максимальный достигнутый': max_score,
                    'Минимальный достигнутый': min_score,
                    'Количество попыток': len(mission_scores)
                })
            
            pivot_df = pd.DataFrame(pivot_data)
            pivot_df.to_excel(writer, sheet_name='Сводка по миссиям', index=False)
        
        output.seek(0)
        return output

# Создаем глобальный экземпляр калькулятора
fll_calculator = FLLCalculator()
