import json


class APIError(Exception):
    def __init__(self, error_code, error_json):
        self.error_code = error_code
        self.error_json = error_json

    def __str__(self):
        return f"APIError: {self.error_code}\n{json.dumps(self.error_json, indent=2)}"
