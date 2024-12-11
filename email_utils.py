import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(subject, body):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    from_email = os.getenv("FROM_EMAIL")
    from_password = os.getenv("FROM_PASSWORD")
    to_email = os.getenv("TO_EMAIL")
    
    if not all([from_email, from_password, to_email]):
        raise ValueError("Email credentials are not fully configured.")
    
    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject

    # Add body to email
    message.attach(MIMEText(body, "plain"))

    # Set up the SMTP connection and send the email
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()  # Can be omitted for TLS
            server.starttls(context=context)  # Secure the connection
            server.login(from_email, from_password)
            server.sendmail(from_email, to_email, message.as_string())
            print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")