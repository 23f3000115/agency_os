# create_owner.py
import bcrypt
from sqlalchemy import create_engine, text

# Replace with your actual database credentials
DB_URL = "postgresql://admin:115044@100.94.61.59:5432/agency_os"

def create_admin():
    engine = create_engine(DB_URL)
    
    email = "owner@agency.com"
    password = "admin123" # Change this!
    name = "Agency Owner"
    role = "owner"
    
    # Hash the password
    salt = bcrypt.gensalt()
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    with engine.connect() as conn:
        sql = text("""
            INSERT INTO users (full_name, email, password_hash, role) 
            VALUES (:name, :email, :pw, :role)
        """)
        conn.execute(sql, {"name": name, "email": email, "pw": hashed_pw, "role": role})
        conn.commit()
        
    print(f"✅ Success! Created {role} account for {email}")

if __name__ == "__main__":
    create_admin()