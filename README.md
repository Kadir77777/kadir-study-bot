# 📚 StudyBuddy Bot

A Discord bot for **organization, motivation, progress tracking, assignments, and quizzes**!

---

## ✅ Features

- **!ping** – Check if the bot is online.
- **!quote** – Get a random motivational quote (ZenQuotes API + local fallback).
- **!due add/list/next/delete** – Track assignments with SQLite persistence.
- **!pomodoro <minutes> / !stop** – Study timer (Pomodoro technique).
- **!progress** – See your total study sessions and minutes.
- **!quiz <topic>** – Take a quiz! (sample with `!quiz default`).
- **!admin** – Admin-only actions.

---

## 🚀 Setup Instructions

1. Navigate to the project folder:
    ```bash
    cd "C:\Users\lilka\OneDrive\Desktop\files"
    ```
2. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Copy `env.example.txt` to `.env` and add your Discord bot token, prefix, and admin user ID:
    ```env
    DISCORD_TOKEN=your_token_here
    COMMAND_PREFIX=!
    ADMIN_USER_ID=your_discord_id
    ```
5. ✅ **Enable Message Content Intent and Server Members Intent** in the Discord Developer Portal for your bot.

---

## 📂 Folder Structure

- `bot.py` – Main bot code.
- `config.py` – Environment and config loader.
- `data/` – Persistent files, database, flashcards.
- `logs/` – Bot log files.
- `diagrams/` – Architecture diagrams.
- `screenshots/` – *(Add screenshots of the bot in Discord here!)*

---

## 🛠 Usage

Run the bot:
```bash
python bot.py
```

**Bot Commands**:
- `!ping`: Bot status
- `!quote`: Get a motivational quote
- `!due add <title> <YYYY-MM-DD>`: Add assignment
- `!due list`: List assignments
- `!pomodoro <minutes>`: Start study timer
- `!stop`: Cancel timer
- `!progress`: Your study stats
- `!quiz default`: Take a sample quiz
- `!admin`: Admin-only

---

## 📸 Screenshots

Add screenshots of:
- `!help`
- `!due add/list`
- `!pomodoro` + `!stop`
- `!progress`
- `!quote`
- `!quiz default`

## 📸 Screenshots

### 1) Help Command
!Help Command

### 2) Due Command (Add & List)
!Due Command

### 3) Pomodoro Start & Stop
![omodoro Command

### 4) Progress After Session
!Progress Command
*Shows: `!progress` reporting 1 session and 1 minute after Pomodoro completion.*

### 5) Quote Command
!Quote Command

### 6) Quiz Command






## 🏗 Architecture

![Architecture Diagram](diagrams/architecture.png)

*(See `architecture_diagram.md` for Mermaid source.)*

---

## 🌐 Hosting

Host your bot 24/7:
- **Railway**, **Heroku**, or **Replit** recommended.
- Set your environment variables (DISCORD_TOKEN, etc.) in their platform dashboards.
- For local hosting, use Windows **Task Scheduler** or a process manager like [`pm2`](https://pm2.keymetrics.io/) or [`screen`](https://linuxize.com/post/how-to-use-linux-screen/).

---

## ✅ Next Steps (Planned Improvements)

- [x] Richer error reporting for all commands
- [x] Add quiz/flashcards
- [x] Show study progress
- [x] Complete documentation & requirements
- [ ] Use Discord embeds for a better UI
- [ ] Add a web dashboard or statistics visualization
- [ ] Scheduled reminders for due dates

---

## 📝 Logs

A sample interactive session log is available in `logs/` demonstrating:
- Bot startup/shutdown
- User commands/responses
- Error handling

---

## 🤝 Contributing

Fork and PRs welcome!
