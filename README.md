# Study Buddy Bot

A Discord bot designed to help you stay organized and motivated while studying.

---

## ✅ Features
- **!ping** – Check bot status.
- **!quote** – Get a random motivational quote.
- **!remind <message>** – Save a reminder.
- **!listreminders** – List all your saved reminders.
- **!admin** – Admin-only command for restricted actions.

---

## 🚀 Setup Instructions
1. Navigate to the project folder:
```bash
cd study_buddy_bot
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
4. Copy `.env.example` to `.env` and add your Discord bot token.

---

## 📂 Folder Structure
- `bot.py` – Main bot file.
- `config.py` – Configuration settings.
- `data/` – Database or persistent files.
- `logs/` – Log files.
- `diagrams/` – Architecture diagrams.

---

## 🛠 Usage
Run the bot:
```bash
python bot.py
```
Then, in Discord, use the following commands:
```
!ping              # Check bot status
!quote             # Get a random quote
!remind Finish math homework  # Save a reminder
!listreminders     # View all reminders
!admin             # Admin-only command
```

---

## 📸 Screenshots
*(Add screenshots of the bot in action here)*

---

## 🌐 Hosting
To keep your bot running 24/7:
- Use **Heroku**, **Railway**, or **Replit**.
- Add your bot token as an environment variable.

---

## ✅ Next Steps
- [x] Add commands
- [x] Implement error handling
- [ ] Add persistence using SQLite or JSON
- [ ] Improve UI with Discord embeds
- [ ] Add logging and monitoring

---

## 🤝 Contributing
Feel free to fork this repo and submit pull requests!

---

## 📝 Logs
A sample interactive session log is available in `logs/sample_session.log`. It demonstrates:
- Bot startup and shutdown
- User commands and bot responses
- Permission handling
