import os, mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
load_dotenv()
c=mysql.connector.connect(host=os.getenv("DB_HOST","localhost"),user=os.getenv("DB_USER","root"),
 password=os.getenv("DB_PASSWORD",""),database=os.getenv("DB_NAME","medicore_hms"))
name=input("Admin name: "); email=input("Admin email: "); password=input("Admin password: ")
cur=c.cursor()
cur.execute("INSERT INTO users(full_name,email,password_hash,role) VALUES(%s,%s,%s,'Admin')",
 (name,email,generate_password_hash(password)))
c.commit(); cur.close(); c.close()
print("Admin account created. Sign in using the email and password you entered.")
