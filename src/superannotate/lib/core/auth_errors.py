from lib.core import CONFIG_INI_FILE_LOCATION

#: Shared between lib.core (entity validation) and lib.infrastructure (token
#: resolution) - lives in core so infrastructure can import it without creating a
#: cycle back into core (core must never import from infrastructure).
INVALID_TOKEN_ERROR = "Invalid token."
INVALID_TEAM_ID_ERROR = "Invalid team id provided."
INVALID_CREDENTIALS_ERROR = "Invalid credentials provided."
CREDENTIALS_NOT_FOUND_ERROR = (
    "Credentials not found: SA_TOKEN environment variable is not set and "
    f"config file '{CONFIG_INI_FILE_LOCATION}' was not found."
)
