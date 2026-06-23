from app.core.database import SessionLocal
from app.services.email import EmailService

def run_email_demo():
    print("⏳ Attempting to send test verification email...")
    
    # Optional: Open database session if you want to test EmailLog tracking
    db = SessionLocal()
    
    try:
        EmailService.send_email(
            recipient_email="jsking982@gmail.com",  # <-- Change to your email
            subject="🚀 Cutover System Live Verification Alert",
            body=(
                "Hello Team,\n\n"
                "This is an automated test verifying that the outbound SMTP "
                "STARTTLS pipeline is functioning perfectly within our unified backend."
            ),
            cc_emails=["secondary_owner@gmail.com"],          # <-- Optional CC recipient
            db=db
        )
        print("✅ Email sent successfully! Check your inbox (and spam folder).")
    except Exception as e:
        print(f"❌ Email dispatch failed: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    run_email_demo()