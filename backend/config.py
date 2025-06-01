"""Configuration constants for the pipeline."""

# LLM Analysis
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BATCH_SIZE = 5
MAX_RETRIES = 3
DEFAULT_TRUNCATION = 1003
DEFAULT_TIMEOUT = 30

# File names
DEFAULT_RAW_DATA = "raw_data.json"
DEFAULT_LOOKUP_TABLE = "lookup_table.json"
DEFAULT_OUTPUT_DIR = "."

# Attachment processing
DEFAULT_ATTACHMENT_RETRIES = 1