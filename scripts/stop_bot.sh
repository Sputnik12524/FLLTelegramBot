#!/bin/bash

# Скрипт для остановки FLL Telegram Bot
# Автор: Assistant

echo "🛑 Остановка FLL Telegram Bot..."

# Проверяем, запущен ли бот
if screen -list | grep -q "fll_bot"; then
    echo "📱 Останавливаем screen сессию 'fll_bot'..."
    screen -X -S fll_bot quit
    
    # Проверяем, что сессия остановлена
    sleep 1
    if ! screen -list | grep -q "fll_bot"; then
        echo "✅ Бот успешно остановлен"
    else
        echo "❌ Ошибка при остановке бота"
        exit 1
    fi
else
    echo "ℹ️  Бот не запущен"
fi 