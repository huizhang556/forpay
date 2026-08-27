"""Run Alembic, including a safe bootstrap for pre-Alembic databases."""
import subprocess
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import get_settings
from app.db.session import engine


def main() -> None:
    config = Config("/app/alembic.ini")
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    required = {
        "payment_channels",
        "orders",
        "payment_events",
        "payment_notifications",
        "merchant_api_keys",
        "callback_attempts",
        "products",
        "product_channels",
    }
    tables = set(inspect(engine).get_table_names())
    version_rows = []
    if "alembic_version" in tables:
        with engine.connect() as connection:
            version_rows = connection.exec_driver_sql("SELECT version_num FROM alembic_version").all()
    if ("alembic_version" not in tables or not version_rows) and required.issubset(tables):
        print("检测到旧版完整数据库，写入 Alembic 当前版本标记")
        command.stamp(config, "head")
    command.upgrade(config, "head")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"数据库迁移失败: {exc}", file=sys.stderr)
        raise
