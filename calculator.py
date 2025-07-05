from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class FLLCalculator:
    def __init__(self):
        self.missions = {
            "mission_1": {"name": "Точность", "max_points": 20},
            "mission_2": {"name": "Сбор урожая", "max_points": 30},
            "mission_3": {"name": "Доставка продуктов", "max_points": 25},
            "mission_4": {"name": "Животные на ферме", "max_points": 20},
            "mission_5": {"name": "Переработка отходов", "max_points": 15},
            "mission_6": {"name": "Солнечная энергия", "max_points": 20},
            "mission_7": {"name": "Водные ресурсы", "max_points": 25},
            "mission_8": {"name": "Инновационный проект", "max_points": 30},
            "mission_9": {"name": "Исследование", "max_points": 15},
            "mission_10": {"name": "Командная работа", "max_points": 20},
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
        max_total = sum(mission["max_points"] for mission in self.missions.values())
        
        control_buttons = [
            InlineKeyboardButton(text=f"📊 Итого: {total_score}/{max_total}", callback_data="calc_total"),
            InlineKeyboardButton(text="🔄 Сбросить", callback_data="calc_reset")
        ]
        buttons.append(control_buttons)
        
        # Изменяем callback_data для кнопки "Назад"
        back_button = [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="calc_back_to_main")]
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
        
        # Добавляем максимальное значение, если его нет в списке
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
            
            max_total = sum(mission["max_points"] for mission in self.missions.values())
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
        
        max_total = sum(mission["max_points"] for mission in self.missions.values())
        breakdown += f"\n🎯 **Общий счет: {total}/{max_total}**"
        
        # Добавляем процент выполнения
        percentage = (total / max_total) * 100 if max_total > 0 else 0
        breakdown += f"\n📈 **Процент выполнения: {percentage:.1f}%**"
        
        return breakdown

# Создаем глобальный экземпляр калькулятора
fll_calculator = FLLCalculator()
