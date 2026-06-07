import asyncpg
from config import DATABASE_URL


class Database:
    """PostgreSQL database handler for storing bot settings."""

    def __init__(self):
        self.pool = None

    async def connect(self):
        """Create a connection pool to the database."""
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self._create_tables()
        print("✅ Database connected successfully!")

    async def disconnect(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            print("🔴 Database disconnected.")

    async def _create_tables(self):
        """Create the required tables if they don't exist."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS start_settings (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    photo_file_id TEXT DEFAULT '',
                    welcome_message TEXT DEFAULT '✨ HI {mention} WELCOME TO OUR BOT 👋',
                    quote_message TEXT DEFAULT '🍥 I''M AN ADVANCED FORWARD BOT WITH SPECIAL FEATURES

⚡ CLICK THE BUTTONS BELOW TO EXPLORE MORE',
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT single_row CHECK (id = 1)
                );
            """)

            # Insert default row if it doesn't exist
            await conn.execute("""
                INSERT INTO start_settings (id)
                VALUES (1)
                ON CONFLICT (id) DO NOTHING;
            """)

    # ─── Start Settings ──────────────────────────────────────────

    async def get_start_settings(self) -> dict:
        """Retrieve the current start message settings."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM start_settings WHERE id = 1")
            if row:
                return dict(row)
            return {
                "photo_file_id": "",
                "welcome_message": "✨ HI {mention} WELCOME TO OUR BOT 👋",
                "quote_message": (
                    "🍥 I'M AN ADVANCED FORWARD BOT WITH SPECIAL FEATURES\n\n"
                    "⚡ CLICK THE BUTTONS BELOW TO EXPLORE MORE"
                ),
            }

    async def set_start_photo(self, file_id: str):
        """Update the start photo file_id."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE start_settings
                SET photo_file_id = $1, updated_at = NOW()
                WHERE id = 1
                """,
                file_id,
            )

    async def set_welcome_message(self, message: str):
        """Update the welcome message text."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE start_settings
                SET welcome_message = $1, updated_at = NOW()
                WHERE id = 1
                """,
                message,
            )

    async def set_quote_message(self, quote: str):
        """Update the quoted message text."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE start_settings
                SET quote_message = $1, updated_at = NOW()
                WHERE id = 1
                """,
                quote,
            )

    async def clear_start_photo(self):
        """Remove the start photo."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE start_settings
                SET photo_file_id = '', updated_at = NOW()
                WHERE id = 1
                """
            )


# Singleton instance
db = Database()
