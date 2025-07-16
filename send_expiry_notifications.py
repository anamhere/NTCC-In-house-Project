import smtplib
from email.mime.text import MIMEText
from pymongo import MongoClient
from datetime import datetime, timedelta
import dateparser
import os
from dotenv import load_dotenv
import os
from dotenv import load_dotenv
import os
from dotenv import load_dotenv
import os
from dotenv import load_dotenv
import os
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

# Get the URI from .env
mongo_uri = os.getenv("MONGO_URI")

# Connect to MongoDB
print("Connecting to MongoDB...")
client = MongoClient(mongo_uri)
client.admin.command("ping")
print("✅ Successfully connected to MongoDB!")

# Optional: Verify DB and collection
db = client["grocery_db"]
print("✅ Using database:", db.name)

load_dotenv()  # This loads variables from .env

# Now safely access them
MONGO_URI = os.environ["MONGO_URI"]
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
TO_EMAIL = os.environ["TO_EMAIL"]

load_dotenv()  # Loads variables from .env

MONGO_URI = os.environ["MONGO_URI"]
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

load_dotenv()  # Load variables from .env

MONGO_URI = os.environ["MONGO_URI"]

# --- CONFIG ---
# MongoDB connection string
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = "grocery_db"
COLLECTION_NAME = "products"

# Email config
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]  # Use App Password for Gmail

# Recipient email
TO_EMAIL = os.environ["TO_EMAIL"]

# --- FUNCTION TO SEND EMAIL ---
def send_email(subject, body, to_email):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Notification email sent successfully.")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# --- MAIN ---
def main():
    try:
        print("🔍 Connecting to MongoDB...")
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful")

        now = datetime.now()
        target_date = now + timedelta(days=3)

        print(f"📅 Checking for products expiring on: {target_date.strftime('%Y-%m-%d')}")

        # Query items expiring exactly in 3 days (+- some hours to be safe)
        lower_bound = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        upper_bound = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        products = list(collection.find({
            "expiry": {
                "$gte": lower_bound,
                "$lte": upper_bound
            }
        }))

        print(f"📦 Found {len(products)} products expiring in 3 days")

        if not products:
            print("✅ No products expiring in 3 days. No email needed.")
            return

        # Prepare email content
        body = "🚨 GROCERY EXPIRY ALERT 🚨\n\n"
        body += f"The following {len(products)} product(s) are expiring in 3 days:\n\n"
        
        for i, p in enumerate(products, 1):
            name = p.get("name", "Unnamed Product")
            expiry = p.get("expiry")
            if isinstance(expiry, str):
                expiry = dateparser.parse(expiry)
            exp_str = expiry.strftime("%Y-%m-%d") if expiry else "Unknown"
            body += f"{i}. 📦 {name}\n   📅 Expires: {exp_str}\n\n"

        body += "⏰ Don't forget to use or dispose of these items soon!\n\n"
        body += "---\n"
        body += "🤖 This is an automated reminder from your AI Grocery Expiry Tracker.\n"
        body += f"📧 Sent on: {now.strftime('%Y-%m-%d at %H:%M:%S UTC')}"

        # Send the email
        subject = f"🚨 {len(products)} Grocery Item(s) Expiring Soon!"
        
        if send_email(subject, body, TO_EMAIL):
            print(f"✅ Successfully sent expiry notification for {len(products)} products")
        else:
            print("❌ Failed to send notification email")

    except Exception as e:
        print(f"❌ Error in main function: {e}")
        raise e

if __name__ == "__main__":
    print("🚀 Starting grocery expiry check...")
    main()
    print("🏁 Grocery expiry check completed!")
from pymongo import MongoClient

client = MongoClient("mongodb+srv://anamherehehe:8JMLZ5Zv7OcWc26B@notesdb.388xh.mongodb.net/grocery_db?retryWrites=true&w=majority&appName=notesDB")
print(client.list_database_names())
