import os


class Config:
    """Configuration for Fathom MCP Server"""

    def __init__(self):
        self.api_key = os.getenv("FATHOM_API_KEY", "")
        self.base_url = "https://api.fathom.ai/external/v1"
        self.timeout = int(os.getenv("FATHOM_TIMEOUT", "30"))
        self.output_format = os.getenv("OUTPUT_FORMAT", "hybrid")
        self.default_per_page = int(os.getenv("DEFAULT_PER_PAGE", "50"))

    def validate(self) -> bool:
        """Validate configuration

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid with detailed error message
        """
        errors = []

        if not self.api_key:
            errors.append("FATHOM_API_KEY is required")

        if not self.base_url:
            errors.append("base_url is required")

        if self.timeout <= 0:
            errors.append("FATHOM_TIMEOUT must be a positive integer")

        if self.default_per_page <= 0:
            errors.append("DEFAULT_PER_PAGE must be a positive integer")

        if self.output_format not in ("toon", "json", "hybrid"):
            errors.append("OUTPUT_FORMAT must be 'toon', 'json', or 'hybrid'")

        if errors:
            raise ValueError("Configuration validation failed: " + "; ".join(errors))

        return True

    @property
    def headers(self) -> dict:
        """Return headers for Fathom API requests"""
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "Fathom-MCP-Server/1.0"
        }


# Global config instance
config = Config()