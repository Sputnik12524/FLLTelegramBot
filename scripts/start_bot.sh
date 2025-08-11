#!/bin/bash

# Скрипт для запуска FLL Telegram Bot
# Автор: Assistant
# Дата: $(date)

echo "🚀 Запуск FLL Telegram Bot..."

# Проверяем, существует ли виртуальное окружение
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаём..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
echo "📦 Активация виртуального окружения..."
source venv/bin/activate

# Устанавливаем необходимые зависимости
echo "🔧 Установка зависимостей..."
if [ -f "scripts/requirements.txt" ]; then
    echo "📋 Найден файл requirements.txt, устанавливаем зависимости..."
    pip install -r scripts/requirements.txt
else
    echo "📦 Файл requirements.txt не найден, устанавливаем зависимости напрямую..."
    pip install aiogram>=3.0.0
    pip install sqlalchemy>=2.0.0
    pip install aiosqlite>=0.19.0
    pip install pandas>=2.0.0
    pip install openpyxl>=3.1.0
fi

# Проверяем, не запущен ли уже бот
if screen -list | grep -q "fll_bot"; then
    echo "⚠️  Бот уже запущен в screen сессии 'fll_bot'"
    echo "📱 Для подключения к сессии выполните: screen -r fll_bot"
    echo "🔄 Для перезапуска сначала остановите: screen -X -S fll_bot quit"
    exit 1
fi

# Создаём новую screen сессию и запускаем бота
echo "🎬 Создание screen сессии 'fll_bot'..."
screen -dmS fll_bot bash -c "source venv/bin/activate && python3 main.py"

# Проверяем, что сессия создалась
sleep 2
if screen -list | grep -q "fll_bot"; then
    echo "✅ Бот успешно запущен в screen сессии 'fll_bot'"
    echo ""
    echo "📱 Полезные команды:"
    echo "   Подключиться к сессии: screen -r fll_bot"
    echo "   Отключиться от сессии: Ctrl+A, затем D"
    echo "   Остановить бота: screen -X -S fll_bot quit"
    echo "   Список сессий: screen -list"
    echo ""
    echo "🔗 Бот будет работать даже после отключения от SSH!"
else
    echo "❌ Ошибка при создании screen сессии"
    exit 1
fi 