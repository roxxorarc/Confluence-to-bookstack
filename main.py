import argparse
from dotenv import dotenv_values
import logging
from confluence_to_bookstack import ConfluenceToBookstack


def parser_setup():
    parser = argparse.ArgumentParser(description="Confluence to BookStack migration tool")
    parser.add_argument("-s", "--source-path", required=True, help="Path to the source Confluence export")
    parser.add_argument("-a", "--attachments", action="store_true", help="Include attachments in the migration")
    return parser


def main():
    parser = parser_setup()
    args = parser.parse_args()
    config = dotenv_values(".env")
    config["source_path"] = args.source_path
    config["attachments"] = args.attachments
    migrator = ConfluenceToBookstack(config)
    if args.attachments:
        migrator.run()
    else:
        migrator.run(attachments=True)


if __name__ == "__main__":
    main()
