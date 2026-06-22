import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import EmailLog

logger = logging.getLogger("EmailService")

class EmailService:
    @staticmethod
    def send_email(recipient_email: str, subject: str, body: str, cc_emails: list = None, db: Session = None):
        """
        Sends a multipart email using SMTP with TLS/STARTTLS and optionally logs it to the database.
        """
        if not recipient_email or not subject or body is None:
            raise ValueError("recipient_email, subject, and body are required.")

        cc_list = []
        if cc_emails:
            if isinstance(cc_emails, str):
                cc_list = [cc_emails.strip()]
            else:
                cc_list = [str(cc).strip() for cc in cc_emails if cc and str(cc).strip()]

        recipients = [recipient_email] + cc_list

        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USERNAME
        msg["To"] = recipient_email
        msg["Subject"] = subject
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.sendmail(settings.SMTP_USERNAME, recipients, msg.as_string())

            logger.info("Email sent successfully to %s cc=%s", recipient_email, cc_list)

            if db is not None:
                email_entry = EmailLog(
                    task_id=None,
                    direction="OUTBOUND",
                    sender=settings.SMTP_USERNAME,
                    recipient=recipient_email,
                    subject=subject,
                    body_content=body,
                    timestamp=datetime.utcnow(),
                )
                db.add(email_entry)
                db.commit()

        except Exception:
            logger.exception("Failed to send email to %s", recipient_email)
            if db is not None:
                db.rollback()
            raise