# CloudBot Host

Professional Python bot-hosting dashboard starter for Render + Firebase.

## Persistent data
User accounts, balances, transactions, plans and bot metadata are stored in Firebase Firestore. Do not store critical billing/account data only on Render's local filesystem.

## Local setup
1. Create a Firebase project and Firestore database.
2. Create a Firebase service account.
3. Set FIREBASE_SERVICE_ACCOUNT_JSON and SECRET_KEY.
4. `pip install -r requirements.txt`
5. `python app.py`

## Render
Deploy using Docker. Set the environment variables in Render:
- SECRET_KEY
- FIREBASE_SERVICE_ACCOUNT_JSON

## Important production work
Actual execution of arbitrary user Python code must be isolated in separate sandboxed workers/containers with CPU/RAM/time limits, network policy, filesystem isolation and abuse controls. The included bot_manager.py is intentionally a placeholder rather than an unsafe arbitrary-code runner.
