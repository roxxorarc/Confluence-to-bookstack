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
    else:
        try:
            migrator.run()
            logger.info("Migration completed successfully.")
        except Exception as e:
            logger.error(f"Migration has been interrupted: {e}")


if __name__ == "__main__":
    main()
