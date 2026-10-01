import pickle
from pathlib import Path
import bcrypt

passwords_to_hash = ["student123", "tutor123"]

hashed_passwords = [
    bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
    for pwd in passwords_to_hash
]

file_path = Path(__file__).parent / "hashed.pw.pkl"
with open(file_path, "wb") as file:
    pickle.dump(hashed_passwords, file)

print("✅ SUCCESS: hashed.pw.pkl has been populated with password hashes!")