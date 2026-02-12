from database.database import init_db

if __name__ == "__main__":
    init_db()
    print("Users table created (if it did not already exist).")
