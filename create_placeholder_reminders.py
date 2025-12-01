
import os
import json
from datetime import datetime

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Create placeholder reminders data
reminders = [
    {
        "user": "Alice",
        "message": "Finish math homework",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    {
        "user": "Bob",
        "message": "Prepare for science quiz",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
]

# Save to data/reminders.json
file_path = "data/reminders.json"
with open(file_path, "w") as f:
    json.dump(reminders, f, indent=4)

print(f"Placeholder reminders file created successfully at {file_path} with {len(reminders)} sample entries.")
