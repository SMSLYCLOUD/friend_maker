import sys
import bcrypt
from app.database.repository import Repository

def create_user(username, password):
    repo = Repository()
    # Check if user exists
    if repo.get_user(username):
        print(f"Error: User '{username}' already exists.")
        return
    
    # Hash password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    repo.create_user(username, hashed)
    print(f"User '{username}' created successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python manage.py create-user <username> <password>")
    else:
        cmd = sys.argv[1]
        if cmd == "create-user":
            create_user(sys.argv[2], sys.argv[3])
        else:
            print(f"Unknown command: {cmd}")
