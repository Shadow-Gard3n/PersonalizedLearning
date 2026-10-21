
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings


client = AsyncIOMotorClient(settings.mongodb_url)
database = client[settings.database_name]

users_collection = database["users"]
sessions_collection = database["learning_sessions"]
questions_collection = database["questions"]
attempts_collection = database["attempts"]
knowledge_collection = database["learner_knowledge"]