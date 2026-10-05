import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# ── DATABASE URL ─────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/medassist_db"
)

# ── ENGINE ───────────────────────────────────────────────────
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── BASE CLASS ───────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ── GET DB SESSION ───────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── TEST CONNECTION ──────────────────────────────────────────
def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print("PostgreSQL connected:", version[:50])
            
            # check all tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            print("Tables found:", tables)
            return True
    except Exception as e:
        print("Connection failed:", e)
        return False

if __name__ == "__main__":
    test_connection()