from confluence_to_bookstack import ConfluenceToBookstack
from config import Config
from utils import setup_logging

def main():
    logger = setup_logging()
    config = Config.load()

    migrator = ConfluenceToBookstack(config)

    try:
        migrator.run()
        logger.info(
            f"Migration started with config: {config.model_dump_json(indent=2)}"
        )
    except Exception as e:
        logger.error(f"Migration failed: {e}")

    logger.info("Migration completed successfully.")


if __name__ == "__main__":
    main()
