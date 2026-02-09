import os

DB_NAME = os.getenv("DB_Name")
DB_USER = os.getenv("DB_User")
DB_PASS = os.getenv("DB_Password")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT") 

class Config:
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
