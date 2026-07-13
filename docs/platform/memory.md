# Memory engine

Short-term, long-term, and conversation memories persist in SQLite. Literal text search and deterministic local token-cosine semantic ranking are operational. Conversation summaries use a deterministic staging implementation. The local semantic provider requires no external model, credential, or network access; a future embedding provider must remain optional and disabled by default.
