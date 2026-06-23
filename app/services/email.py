import logging
import smtplib
import imaplib
import email
from email.policy import default
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import EmailLog

logger = logging.getLogger("EmailService")

class EmailService:
    # =====================================================
    # OUTBOUND (SMTP / Sender)
    # =====================================================
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


    # =====================================================
    # INBOUND (IMAP / Listener)
    # =====================================================
    @staticmethod
    def fetch_unread_emails() -> list:
        """Logs into the inbox, finds unread emails, parses them, and marks them as read."""
        inbound_messages = []
        try:
            # Note: Make sure IMAP_SERVER is in your settings (e.g., "imap.gmail.com" or "outlook.office365.com")
            imap_server = getattr(settings, "IMAP_SERVER", "imap.gmail.com")

            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            mail.select('INBOX')

            # Search for UNSEEN (unread) emails
            status, messages = mail.search(None, 'UNSEEN')
            
            if status != "OK":
                logger.error("Failed to search inbox.")
                return []

            email_ids = messages[0].split()
            if not email_ids:
                return []

            logger.info(f"Found {len(email_ids)} new unread emails.")

            # Process each unread email
            for e_id in email_ids:
                res, msg_data = mail.fetch(e_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1], policy=default)
                        
                        subject = msg.get('subject', '')
                        sender = msg.get('from', '')
                        body = EmailService._extract_text_body(msg)

                        inbound_messages.append({
                            "sender": sender,
                            "subject": subject,
                            "text_body": body
                        })

                        # Optional: Log INBOUND email to database here if you want
                        # You could add an EmailLog entry just like in send_email

            mail.close()
            mail.logout()
            return inbound_messages

        except Exception as e:
            logger.error("Error fetching emails via IMAP", exc_info=True)
            return []

    @staticmethod
    def _extract_text_body(msg) -> str:
        """Helper to extract plain text from an email, handling multipart messages."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                # Look specifically for the plain text part of the email
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return body.strip()