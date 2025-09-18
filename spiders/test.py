from werkzeug.security import generate_password_hash
from utils.query import query
users = query(
    "SELECT username, password FROM user",
    [],
    'select'
)
for username, password in users:
    if not password.startswith("pbkdf2:"):
        hashed = generate_password_hash(password, method='pbkdf2:sha256')
        query(
            "UPDATE user SET password = %s WHERE username = %s",
            [hashed, username]
        )