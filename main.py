from dotenv import dotenv_values
from confluence_to_bookstack import ConfluenceToBookstack
from config import Config, parser_setup
from utils import setup_logging

def main():
    logger = setup_logging()
    parser = parser_setup()
    args = parser.parse_args()
    env_values = dotenv_values(".env")
    config = Config.from_env_and_args(env_values, args)
    migrator = ConfluenceToBookstack(config)

    logger.info(f"Migration started with config: {config.model_dump_json(indent=2)}")

    migrator.run()


if __name__ == "__main__":
    main()
