import os
import smtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = "email-smtp.us-east-1.amazonaws.com"
SMTP_PORT = 587


def generate_temp_password(full_name: str) -> str:
    name_part   = full_name.strip().replace(" ", "")[:4].title()
    random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
    return f"{name_part}@{random_part}"


def send_welcome_email(to_email: str, full_name: str, temp_password: str, role: str):
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    sender    = os.getenv("SMTP_FROM", "")
    app_url   = os.getenv("APP_URL", "http://localhost:3001")

    if not smtp_user or not smtp_pass or not sender:
        raise Exception("SMTP_USER, SMTP_PASSWORD or SMTP_FROM not set in .env")

    role_label = {
        "super_admin": "Super Admin",
        "admin":       "Admin",
        "user":        "User (View Only)",
    }.get(role, role)

    msg            = MIMEMultipart()
    msg['From']    = sender
    msg['To']      = to_email
    msg['Subject'] = "Your RecruitAI Access — NickelFox Technologies"

    body = f"""Hello {full_name},

You have been granted access to RecruitAI at NickelFox Technologies as {role_label}.

Your login credentials:

  Login URL:           {app_url}
  Email:               {to_email}
  Temporary Password:  {temp_password}

This temporary password expires in 24 hours.
You will be asked to set a new password on your first login.

If you have any issues, please contact your administrator.

Best regards,
Director
"""

    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(sender, to_email, msg.as_string())

    print(f"[Email] Welcome email sent to {to_email}")
