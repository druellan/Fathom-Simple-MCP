import os

class Config:
    """Configuration for Fathom MCP Server"""

    def __init__(self):
        self.api_key = os.getenv("FATHOM_API_KEY", "")
        self.base_url = "https://api.fathom.ai/external/v1"
        self.timeout = int(os.getenv("FATHOM_TIMEOUT", "30"))
        self.output_format = os.getenv("OUTPUT_FORMAT", "toon")
        self.default_per_page = int(os.getenv("DEFAULT_PER_PAGE", "50"))

    def validate(self) -> bool:
        """Validate configuration"""
        return bool(self.api_key and self.base_url)

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