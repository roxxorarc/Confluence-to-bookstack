from pydantic import BaseModel
import argparse

class Config(BaseModel):
    source_path: str
    attachments: bool = False

    class Config:
        extra = "allow"

    @classmethod
    def from_env_and_args(cls, env_values: dict, source_path: str, attachments: bool):
        config_data = env_values.copy()
        config_data["source_path"] = source_path
        config_data["attachments"] = attachments
        return cls(**config_data)




def parser_setup():
    parser = argparse.ArgumentParser(description="Confluence to BookStack migration tool")
    parser.add_argument("-s", "--source-path", required=True, help="Path to the source Confluence export")
    parser.add_argument("-a", "--attachments", action="store_true", help="Include attachments in the migration")
    return parser


