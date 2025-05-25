import smtplib
from email.mime.text import MIMEText
from pymongo import MongoClient
from datetime import datetime, timedelta
import dateparser
import os
from dotenv import load_dotenv
load_dotenv()
# --- CONFIG ---

# MongoDB connection string
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = "grocery_db"
COLLECTION_NAME = "products"

# Email config - replace with your details
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")"
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587)
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"] # Use App Password for Gmail

# Recipient email (could be same as sender or user email)
TO_EMAIL = os.environ["TO_EMAIL"]

# --- FUNCTION TO SEND EMAIL ---
def send_email(subject, body, to_email):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
    print("Notification email sent.")

# --- MAIN ---
def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    now = datetime.now()
    target_date = now + timedelta(days=3)

    # Query items expiring exactly in 3 days (+- one day to be safe)
    lower_bound = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    upper_bound = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    products = list(collection.find({
        "expiry": {
            "$gte": lower_bound,
            "$lte": upper_bound
        }
    }))

    if not products:
        print("No products expiring in 3 days. No email sent.")
        return

    # Prepare email content
    body = "The following products are expiring in 3 days:\n\n"
    for p in products:
        name = p.get("name", "Unnamed")
        expiry = p.get("expiry")
        if isinstance(expiry, str):
            expiry = dateparser.parse(expiry)
        exp_str = expiry.strftime("%Y-%m-%d") if expiry else "Unknown"
        body += f"- {name} (Expiry: {exp_str})\n"

    # Send the email
    send_email("Grocery Expiry Reminder - Items Expiring Soon", body, TO_EMAIL)


if __name__ == "__main__":
    main()
