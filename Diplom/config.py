import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'gX7yZ2vK8wQ9tU5rI0pL4jH1fG3dE6cO'  # Для защиты от CSRF
    DEBUG = True  # Включить режим отладки

class DevelopmentConfig(Config):
    # Настройки для разработки
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:1999@localhost:5432/finance_db' 
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Отключить отслеживание изменений

class ProductionConfig(Config):
    # Настройки для продакшена
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:1999@host:port/database_name' 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
config = DevelopmentConfig

