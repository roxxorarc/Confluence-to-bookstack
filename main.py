import argparse
from dotenv import dotenv_values
import logging
from etl import extract_confluence_data, transform_data, load_data_to_bookstack, load_with_attachments


def parser_setup():
    parser = argparse.ArgumentParser(description="Confluence to BookStack migration tool")
    parser.add_argument("-s", "--source-path", required=True, help="Path to the source Confluence export")
    parser.add_argument("-a", "--attachments", action="store_true", help="Include attachments in the migration")
    return parser



def main():
    parser = parser_setup()
    args = parser.parse_args()
    config = dotenv_values(".env")

    data = extract_confluence_data(args.source_path)

    if args.attachments:
        load_with_attachments(data, config)
    else:
        load_data_to_bookstack(data, config)


if __name__ == "__main__":
    main()