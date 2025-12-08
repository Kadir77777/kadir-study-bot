# Study Buddy Bot  
### Module 9 + Module 10 – Complete Build + New Feature Iteration

Study Buddy Bot helps students stay organized with assignments, reminders, quizzes, Pomodoro timers, progress tracking, and now includes a Study Leaderboard added in Module 10.

---

## 🆕 New Feature for Module 10: Study Leaderboard

### Command:
!leaderboard

### Example Output:
🏆 Study Leaderboard  
#1 — username: 42 minutes  
#2 — anotherUser: 12 minutes  

### What This Feature Does:
- Reads study session data from SQLite database
- Groups and sums minutes by user
- Ranks users from highest to lowest
- Displays top 10 users

This feature enhances motivation and engagement by making study progress visible.

---

## 📌 Features List (Complete)

### Assignment Tracker (`!due`)
- Add, list, delete assignments  
- View next due assignment  

### Pomodoro Timer (`!pomodoro`)
- Starts study session  
- Logs minutes to DB  
- Cancel with `!stop`

### Progress Tracker (`!progress`)
- Shows number of sessions + total minutes studied

### Quiz Feature (`!quiz <topic>`)
- Loads questions from JSON  
- Randomized 5-question mini quiz  

### Daily Reminders System
- `!setreminderhere`  
- `!remind <text>`  
- `!listreminders`  
- `!deletereminder`  

### Other Commands
- `!admin`  
- `!usercount`  
- `!ping`  
- Custom `!help`

---

## 🏗 Updated Flow (Module 10 Feature)

