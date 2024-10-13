# notification.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import logging
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


class EmailNotifier:
    """
    A class to handle sending email notifications.
    """

    def __init__(self):
        # Load SMTP configuration from environment variables
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.use_tls = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")

        
        recipients = os.getenv("EMAIL_RECIPIENTS", "")
        self.recipients = [email.strip() for email in recipients.split(",") if email.strip()]

        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password, self.recipients]):
            print("Email notifier is not fully configured. Please check environment variables.")
            self.is_configured = False
        else:
            self.is_configured = True

    def send_email(self, subject: str, body: str):
        
        if not self.is_configured:
            print("Email notifier is not configured properly. Skipping email send.")
            return

        try:
            # Create a multipart message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ", ".join(self.recipients)
            msg['Subject'] = subject

            
            msg.attach(MIMEText(body, 'plain'))

            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()

            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.from_email, self.recipients, msg.as_string())
            server.quit()

            print(f"Email sent successfully to {self.recipients}")

        except Exception as e:
            print("Task Complete")
