#!/bin/bash

# Скрипт для перезапуска FLL Telegram Bot
# Автор: Assistant

echo "🔄 Перезапуск FLL Telegram Bot..."

# Останавливаем бота
echo "🛑 Останавливаем бота..."
./stop_bot.sh

# Ждём немного
sleep 2

# Запускаем бота
echo "🚀 Запускаем бота..."
./start_bot.sh 