from confluence_to_bookstack import ConfluenceToBookstack
from config import Config, parser_setup
from utils import logger


def main():
    args = parser_setup()
    config = Config.load(args)
    migrator = ConfluenceToBookstack(config)
    if args.clear:
        migrator.clear()
        logger.info("Data cleared")
        exit(0)
    try:
        migrator.run()
    except Exception as e:
        logger.error(f"Migration failed: {e}")

    logger.info("Migration completed successfully.")


if __name__ == "__main__":
    main()
