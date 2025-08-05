from dotenv import dotenv_values
import logging
from confluence_to_bookstack import ConfluenceToBookstack
from config import Config, parser_setup

def main():
    parser = parser_setup()
    args = parser.parse_args()
    env_values = dotenv_values(".env")
    config = Config.from_env_and_args(env_values, args.source_path, args.attachments)
    migrator = ConfluenceToBookstack(config)
    if args.attachments:
        migrator.run()
    else:
        migrator.run(attachments=True)


if __name__ == "__main__":
    main()
