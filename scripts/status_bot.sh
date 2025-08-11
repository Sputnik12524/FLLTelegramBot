#!/bin/bash

# Скрипт для проверки статуса FLL Telegram Bot
# Автор: Assistant

echo "📊 Статус FLL Telegram Bot"
echo "=========================="

# Проверяем screen сессии
if screen -list | grep -q "fll_bot"; then
    echo "✅ Бот запущен в screen сессии 'fll_bot'"
    
    # Показываем информацию о сессии
    echo ""
    echo "📱 Информация о сессии:"
    screen -list | grep "fll_bot"
    
    # Проверяем процессы Python
    echo ""
    echo "🐍 Процессы Python:"
    ps aux | grep "main.py" | grep -v grep || echo "   Процессы не найдены"
    
else
    echo "❌ Бот не запущен"
fi

echo ""
echo "🔧 Полезные команды:"
echo "   Запустить: ./start_bot.sh"
echo "   Остановить: ./stop_bot.sh"
echo "   Перезапустить: ./restart_bot.sh"
echo "   Подключиться к сессии: screen -r fll_bot" 