# TEST PLAN for Study Buddy Bot

## 1. Objective
To verify that all implemented commands and features of Study Buddy Bot work as expected in a Discord environment.

## 2. Scope
- Functional testing of bot commands.
- Validation of persistence (if implemented).
- Error handling and permission checks.

## 3. Test Environment
- Discord server with bot added.
- Python version: 3.x
- Dependencies installed from requirements.txt

## 4. Test Cases
| Test Case ID | Command | Expected Result | Actual Result | Pass/Fail |
|--------------|---------|-----------------|---------------|-----------|
| TC-01 | !ping | Bot responds with "Bot is online" or similar | | |
| TC-02 | !quote | Bot returns a random motivational quote | | |
| TC-03 | !remind Finish math homework | Bot confirms reminder saved | | |
| TC-04 | !listreminders | Bot lists all saved reminders | | |
| TC-05 | !admin | If user is admin: executes command; else: permission error | | |
| TC-06 | Invalid command (e.g., !xyz) | Bot responds with error/help message | | |

## 5. Pass/Fail Criteria
- All commands respond correctly according to expected results.
- No crashes or unhandled exceptions.

## 6. Notes
- Include screenshots of successful command execution.
- Log all interactions in logs/ folder.
