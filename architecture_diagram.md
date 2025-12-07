# StudyBuddy Bot – Architecture Diagram

```mermaid
flowchart TD
    U[User on Discord] -->|commands| G[Discord Gateway]
    G -->|events & messages| B[discord.py Bot]

    subgraph Commands Layer
    B --> H[Help / Ping]
    B --> DUE[Due Tracker]
    B --> POMO[Pomodoro]
    B --> PROG[Progress]
    B --> QUIZ[Quiz]
    end

    subgraph Persistence
    DB[(SQLite: data/bot.db)]
    end

    DUE -->|INSERT/SELECT/DELETE| DB
    POMO -->|INSERT sessions| DB
    PROG -->|SELECT aggregates| DB

    subgraph External APIs & Files
    ZQ[ZenQuotes API]
    LQ[Local Quotes: data/quotes.json]
    FC[Flashcards: data/flashcards/*.json]
    end

    QUIZ -->|read questions| FC
    H -->|read prefix & token| CFG[config.py + .env]
    B -->|loads config| CFG
    H -->|fallback quotes| LQ
    H -->|fetch quotes| ZQ

    note over B,DB: Error handling & logging -> logs/bot.log
```

**Notes**
- Commands are routed by discord.py, using your `COMMAND_PREFIX` from `.env` via `config.py`.
- Persistence uses SQLite (`data/bot.db`) for assignments and study sessions.
- Quotes use ZenQuotes with a local JSON fallback.
- Quiz reads from JSON files in `data/flashcards/`.
- Logs go to `logs/bot.log`.
