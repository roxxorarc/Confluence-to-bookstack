import requests


class ConfluenceToBookstack:
    def __init__(self, config):
        self.config = config
        self.data = None

    def run(self, attachments: bool = False):
        print(self.config.source_path)

        if self.config.attachments:
            pass
        else:
            pass
