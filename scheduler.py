import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import User
from database.engine import async_session_factory

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReminderScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.reminder_task = None
        
    async def start(self):
        """Запускает планировщик напоминаний"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return
            
        self.is_running = True
        self.reminder_task = asyncio.create_task(self._run_scheduler())
        logger.info("Планировщик напоминаний запущен")
        
    async def stop(self):
        """Останавливает планировщик напоминаний"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.reminder_task:
            self.reminder_task.cancel()
            try:
                await self.reminder_task
            except asyncio.CancelledError:
                pass
        logger.info("Планировщик напоминаний остановлен")
        
    async def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.is_running:
            try:
                await self._check_and_send_reminders()
                # Проверяем каждый час
                await asyncio.sleep(3600)  # 1 час = 3600 секунд
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                await asyncio.sleep(300)  # При ошибке ждем 5 минут
                
    async def _check_and_send_reminders(self):
        """Проверяет и отправляет напоминания пользователям"""
        try:
            async with async_session_factory() as session:
                # Получаем всех пользователей, которым нужно отправить напоминание
                users_to_remind = await self._get_users_needing_reminder(session)
                
                if not users_to_remind:
                    logger.info("Нет пользователей для напоминания")
                    return
                    
                logger.info(f"Найдено {len(users_to_remind)} пользователей для напоминания")
                
                # Отправляем напоминания
                for user in users_to_remind:
                    try:
                        await self._send_reminder(user.tg_id)
                        await self._update_reminder_time(session, user.tg_id)
                        logger.info(f"Напоминание отправлено пользователю {user.tg_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания пользователю {user.tg_id}: {e}")
                        
                await session.commit()
                
        except Exception as e:
            logger.error(f"Ошибка при проверке напоминаний: {e}")
            
    async def _get_users_needing_reminder(self, session: AsyncSession) -> List[User]:
        """Получает список пользователей, которым нужно отправить напоминание"""
        # Дата 2 недели назад
        two_weeks_ago = datetime.now() - timedelta(weeks=2)
        
        # Получаем пользователей, которым либо никогда не отправлялось напоминание,
        # либо последнее напоминание было более 2 недель назад
        query = select(User).where(
            (User.last_photo_reminder.is_(None)) |
            (User.last_photo_reminder <= two_weeks_ago)
        )
        
        result = await session.execute(query)
        return result.scalars().all()
        
    async def _send_reminder(self, user_tg_id: int):
        """Отправляет напоминание конкретному пользователю"""
        reminder_text = (
            "📸 Привет! Напоминаю о важном!\n\n"
            "Уже прошло 2 недели с последнего напоминания. "
            "Не забудь прислать фотографию! 📷\n\n"
            "Присылай свои фото через бота с подписью #фоторобота - это поможет тебе отслеживать прогресс! 😊"
        )
        
        try:
            await self.bot.send_message(
                chat_id=user_tg_id,
                text=reminder_text
            )
        except Exception as e:
            # Если пользователь заблокировал бота или удалил аккаунт
            logger.warning(f"Не удалось отправить сообщение пользователю {user_tg_id}: {e}")
            
    async def _update_reminder_time(self, session: AsyncSession, user_tg_id: int):
        """Обновляет время последнего напоминания для пользователя"""
        await session.execute(
            update(User)
            .where(User.tg_id == user_tg_id)
            .values(last_photo_reminder=datetime.now())
        )
        
    async def force_reminder_for_user(self, user_tg_id: int):
        """Принудительно отправляет напоминание конкретному пользователю (для админов)"""
        try:
            await self._send_reminder(user_tg_id)
            
            async with async_session_factory() as session:
                await self._update_reminder_time(session, user_tg_id)
                await session.commit()
                
            return True
        except Exception as e:
            logger.error(f"Ошибка при принудительном напоминании пользователю {user_tg_id}: {e}")
            return False
            
    async def get_users_reminder_status(self) -> List[dict]:
        """Получает статус напоминаний для всех пользователей (для админов)"""
        try:
            async with async_session_factory() as session:
                query = select(User)
                result = await session.execute(query)
                users = result.scalars().all()
                
                status_list = []
                for user in users:
                    status = {
                        'tg_id': user.tg_id,
                        'last_reminder': user.last_photo_reminder,
                        'needs_reminder': self._user_needs_reminder(user.last_photo_reminder)
                    }
                    status_list.append(status)
                    
                return status_list
        except Exception as e:
            logger.error(f"Ошибка при получении статуса напоминаний: {e}")
            return []
            
    def _user_needs_reminder(self, last_reminder: datetime = None) -> bool:
        """Проверяет, нужно ли пользователю напоминание"""
        if last_reminder is None:
            return True
            
        two_weeks_ago = datetime.now() - timedelta(weeks=2)
        return last_reminder <= two_weeks_ago

# Глобальный экземпляр планировщика
reminder_scheduler: ReminderScheduler = None

def get_reminder_scheduler() -> ReminderScheduler:
    """Получает экземпляр планировщика напоминаний"""
    return reminder_scheduler

def init_reminder_scheduler(bot: Bot):
    """Инициализирует планировщик напоминаний"""
    global reminder_scheduler
    reminder_scheduler = ReminderScheduler(bot)
    return reminder_scheduler