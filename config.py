from typing import Optional
from dotenv import dotenv_values
from pydantic import BaseModel
import argparse


class Config(BaseModel):
    class Config:
        extra = "allow"

    @classmethod
    def load(cls, args: Optional[argparse.Namespace] = None):
        env_values = dotenv_values(".env")
        config_data = env_values.copy()
        cli_overrides = {
            "SOURCE_PATH": args.source_path,
            "BOOKSTACK_URL": args.bookstack_url,
            "BOOKSTACK_ID": args.bookstack_id,
            "BOOKSTACK_SECRET": args.bookstack_secret,
        }
        config_data.update({k: v for k, v in cli_overrides.items() if v is not None})

        return cls(**config_data)


def parser_setup():
    parser = argparse.ArgumentParser(description="Confluence to BookStack migration tool")
    parser.add_argument("-s", "--source-path", help="Path to the Confluence export")
    parser.add_argument("-url", "--bookstack-url", help="BookStack API URL")
    parser.add_argument("-id", "--bookstack-id", help="BookStack API ID")
    parser.add_argument("-secret", "--bookstack-secret", help="BookStack API Secret")
    parser.add_argument("-c", "--clear", action="store_true", help="Clear existing BookStack content before migration")
    args = parser.parse_args()
    return args
