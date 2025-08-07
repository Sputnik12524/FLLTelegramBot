import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class LocalResult:
    """Локальный результат пользователя"""
    id: int
    user_tg_id: int
    mission_scores: Dict[str, int]
    total_score: int
    max_possible_score: int
    created_at: str
    name: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Преобразует результат в словарь для сохранения"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LocalResult':
        """Создает результат из словаря"""
        return cls(**data)


class LocalStorage:
    """Система локального хранения результатов"""
    
    def __init__(self, storage_dir: str = "user_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._next_id = 1
    
    def _get_user_file(self, user_id: int) -> Path:
        """Получает путь к файлу пользователя"""
        return self.storage_dir / f"user_{user_id}.json"
    
    def _load_user_data(self, user_id: int) -> List[LocalResult]:
        """Загружает данные пользователя из файла"""
        user_file = self._get_user_file(user_id)
        if not user_file.exists():
            return []
        
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results = []
                for result_data in data.get('results', []):
                    results.append(LocalResult.from_dict(result_data))
                return results
        except (json.JSONDecodeError, KeyError, TypeError):
            # Если файл поврежден, возвращаем пустой список
            return []
    
    def _save_user_data(self, user_id: int, results: List[LocalResult]):
        """Сохраняет данные пользователя в файл"""
        user_file = self._get_user_file(user_id)
        data = {
            'user_id': user_id,
            'results': [result.to_dict() for result in results]
        }
        
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_next_id(self, user_id: int) -> int:
        """Получает следующий ID для результата пользователя"""
        results = self._load_user_data(user_id)
        if not results:
            return 1
        return max(result.id for result in results) + 1
    
    def save_result(self, user_id: int, mission_scores: Dict[str, int], 
                   total_score: int, max_possible_score: int, name: Optional[str] = None) -> LocalResult:
        """Сохраняет результат пользователя"""
        results = self._load_user_data(user_id)
        
        # Создаем новый результат
        new_result = LocalResult(
            id=self._get_next_id(user_id),
            user_tg_id=user_id,
            mission_scores=mission_scores,
            total_score=total_score,
            max_possible_score=max_possible_score,
            created_at=datetime.now().isoformat(),
            name=name
        )
        
        results.append(new_result)
        self._save_user_data(user_id, results)
        return new_result
    
    def get_user_results(self, user_id: int) -> List[LocalResult]:
        """Получает все результаты пользователя"""
        return self._load_user_data(user_id)
    
    def get_result_by_id(self, user_id: int, result_id: int) -> Optional[LocalResult]:
        """Получает конкретный результат по ID"""
        results = self._load_user_data(user_id)
        for result in results:
            if result.id == result_id:
                return result
        return None
    
    def delete_result(self, user_id: int, result_id: int) -> bool:
        """Удаляет результат пользователя"""
        results = self._load_user_data(user_id)
        original_count = len(results)
        
        # Удаляем результат с указанным ID
        results = [r for r in results if r.id != result_id]
        
        if len(results) < original_count:
            self._save_user_data(user_id, results)
            return True
        return False
    
    def get_results_by_period(self, user_id: int, start_date: Optional[datetime] = None) -> List[LocalResult]:
        """Получает результаты пользователя за определенный период"""
        results = self._load_user_data(user_id)
        
        if start_date is None:
            return results
        
        # Фильтруем результаты по дате
        filtered_results = []
        for result in results:
            result_date = datetime.fromisoformat(result.created_at)
            if result_date >= start_date:
                filtered_results.append(result)
        
        return filtered_results
    
    def clear_user_data(self, user_id: int):
        """Очищает все данные пользователя"""
        user_file = self._get_user_file(user_id)
        if user_file.exists():
            user_file.unlink()


# Создаем глобальный экземпляр хранилища
local_storage = LocalStorage() 