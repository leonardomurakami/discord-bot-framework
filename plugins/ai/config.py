"""Constants for the AI plugin."""

from __future__ import annotations

# acpbox OpenAI-compatible Chat Completions path (appended to settings.acpbox_url).
CHAT_COMPLETIONS_PATH = "/v1/chat/completions"

# Discord message length limit. We reserve room for a footer crediting the model.
DISCORD_MESSAGE_LIMIT = 2000
FOOTER_RESERVE = 80  # chars reserved for the model-crediting footer + newline

# Maximum character length of a user's prompt before it is rejected as over-length.
MAX_PROMPT_LENGTH = 4000

# Footer template appended to AI replies.
FOOTER_TEMPLATE = "\n\n_— model: {model}_"

# Truncation indicator appended when an AI reply is truncated to fit Discord.
TRUNCATION_INDICATOR = "…"
