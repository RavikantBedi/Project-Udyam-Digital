import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from sqlmodel import Session
from app.core.config import get_settings
from app.core.db import engine
from app.models.models import NotificationLog
import httpx

settings = get_settings()


def safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def log_notification(channel: str, recipient: str, message: str, subject: str = "", order_id: Optional[str] = None):
    try:
        with Session(engine) as session:
            log = NotificationLog(
                channel=channel,
                recipient=recipient,
                subject=subject,
                message=message,
                status="delivered",
                order_id=order_id,
                created_at=datetime.utcnow()
            )
            session.add(log)
            session.commit()
    except Exception as e:
        safe_print(f"[NotificationLog] Error saving notification: {e}")


def send_email(to_email: str, subject: str, body: str, order_id: Optional[str] = None) -> bool:
    """Send real email via SMTP if configured, otherwise log and deliver to notification center."""
    sent = False
    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.smtp_from
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
                sent = True
                safe_print(f"[Email] Real SMTP email sent to {to_email}")
        except Exception as e:
            safe_print(f"[Email] SMTP error: {e}")
    else:
        safe_print(f"[Email] (Live Center) To: {to_email} | Subject: {subject}")
        sent = True

    log_notification("email", to_email, body, subject=subject, order_id=order_id)
    return sent


def send_sms(phone: str, message: str, order_id: Optional[str] = None) -> bool:
    """Send real SMS via Twilio/Fast2SMS if configured, otherwise deliver to notification center."""
    sent = False
    if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_sms_from:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
            data = {
                "From": settings.twilio_sms_from,
                "To": phone if phone.startswith("+") else f"+91{phone}",
                "Body": message
            }
            res = httpx.post(url, data=data, auth=(settings.twilio_account_sid, settings.twilio_auth_token), timeout=5)
            if res.status_code in (200, 201):
                sent = True
                safe_print(f"[SMS] Twilio SMS dispatched to {phone}")
        except Exception as e:
            safe_print(f"[SMS] Gateway error: {e}")
    else:
        safe_print(f"[SMS] (Live Center) To: {phone} | {message}")
        sent = True

    log_notification("sms", phone, message, order_id=order_id)
    return sent


def send_whatsapp(phone: str, message: str, order_id: Optional[str] = None) -> bool:
    """Send real WhatsApp message via Twilio or Meta Cloud API if configured, otherwise deliver to live feed."""
    sent = False
    if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_whatsapp_from:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
            from_wa = settings.twilio_whatsapp_from
            if not from_wa.startswith("whatsapp:"):
                from_wa = f"whatsapp:{from_wa}"
            to_wa = phone if phone.startswith("+") else f"+91{phone}"
            if not to_wa.startswith("whatsapp:"):
                to_wa = f"whatsapp:{to_wa}"

            data = {
                "From": from_wa,
                "To": to_wa,
                "Body": message
            }
            res = httpx.post(url, data=data, auth=(settings.twilio_account_sid, settings.twilio_auth_token), timeout=5)
            if res.status_code in (200, 201):
                sent = True
                safe_print(f"[WhatsApp] Twilio WhatsApp sent to {phone}")
        except Exception as e:
            safe_print(f"[WhatsApp] Gateway error: {e}")
    else:
        safe_print(f"[WhatsApp] (Live Center) To: {phone} | {message}")
        sent = True

    log_notification("whatsapp", phone, message, order_id=order_id)
    return sent


def notify_user_step(event_type: str, user_email: str, user_phone: str, order_id: str = "", details: dict = None):
    """Notify user across Email, SMS and WhatsApp for lifecycle events."""
    details = details or {}
    bname = details.get("business_name", "Your Business")
    order_num = order_id or "ORD-PENDING"

    if event_type == "signin":
        now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
        sub = f"Security Alert: Sign-in to Accel Business ({bname})"
        body = f"""
        <div style="font-family: Arial, sans-serif; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px;">
            <h2 style="color: #E40000; margin-top:0;">Accel Business Sign-in Alert</h2>
            <p>Hello <strong>{bname}</strong>,</p>
            <p>You have successfully signed in to your Accel Business Udyam Digital account at <strong>{now_str}</strong>.</p>
            <p>If this was not you, please contact support immediately.</p>
            <hr style="border:none; border-top:1px solid #e5e7eb; margin: 15px 0;">
            <p style="font-size:12px; color:#6b7280;">Accel Business · Udyam Digital Platform</p>
        </div>
        """
        sms_msg = f"Accel Business: Sign-in detected for {bname} at {now_str}. Welcome back!"
        wa_msg = f"[Security Alert] Successful sign-in to Udyam Digital for *{bname}* on {now_str}."

        send_email(user_email, sub, body)
        send_sms(user_phone, sms_msg)
        send_whatsapp(user_phone, wa_msg)

    elif event_type == "signup":
        sub = f"Welcome to Accel Business Udyam Digital - {bname}"
        body = f"""
        <div style="font-family: Arial, sans-serif; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px;">
            <h2 style="color: #E40000; margin-top:0;">Welcome to Accel Business!</h2>
            <p>Dear <strong>{bname}</strong>,</p>
            <p>Your business digital onboarding account has been created successfully. You can now discover tailored telecom bundles, perform instant GSTIN/Udyam KYC, and track activation in one sitting.</p>
            <p><a href="http://localhost:5173/advisor" style="background-color:#E40000; color:white; padding:10px 18px; text-decoration:none; border-radius:6px; font-weight:bold; display:inline-block; margin-top:10px;">Start Business Discovery</a></p>
        </div>
        """
        sms_msg = f"Welcome to Accel Business {bname}! Your digital onboarding account is ready. Discover your custom bundle now."
        wa_msg = f"*Welcome to Accel Business, {bname}!*\\n\\nYour business account is active. Connect your clinic, shop, or office in one sitting with transparent pricing and instant KYC."

        send_email(user_email, sub, body)
        send_sms(user_phone, sms_msg)
        send_whatsapp(user_phone, wa_msg)

    elif event_type == "quote_accepted":
        monthly = details.get("monthly_total", 4299)
        bundle_name = details.get("bundle_name", "Business Digital Bundle")
        wa_msg = f"*Quote Accepted - {order_num}*\\n\\nPlan: *{bundle_name}*\\nMonthly Tariff: *INR {monthly:,} + 18% GST*\\nNext Step: Complete quick KYC in 2 minutes: http://localhost:5173/kyc"
        sms_msg = f"Accel Business: Quote accepted for {bundle_name} (INR {monthly}/mo). Complete KYC to schedule install: http://localhost:5173/kyc"
        send_whatsapp(user_phone, wa_msg, order_id=order_num)
        send_sms(user_phone, sms_msg, order_id=order_num)

    elif event_type == "kyc_verified":
        wa_msg = f"*[KYC Verified] Order {order_num}*\\n\\nAll registry and identity checks passed successfully! Your service installation is being scheduled. Live tracker: http://localhost:5173/track"
        sms_msg = f"Accel Business: KYC verified for order {order_num}! Installation team has been notified."
        send_whatsapp(user_phone, wa_msg, order_id=order_num)
        send_sms(user_phone, sms_msg, order_id=order_num)

    elif event_type == "installation_scheduled":
        slot = details.get("slot", "Tomorrow 10:00 AM - 1:00 PM")
        tech_name = details.get("technician", "Vikram Singh (+91 98765 12345)")
        wa_msg = f"*[Installation Scheduled] Order {order_num}*\\n\\nTime Slot: *{slot}*\\nField Engineer: *{tech_name}*\\nPlease ensure premises access."
        sms_msg = f"Accel Business: Engineer scheduled for {slot}. Contact: {tech_name}."
        send_whatsapp(user_phone, wa_msg, order_id=order_num)
        send_sms(user_phone, sms_msg, order_id=order_num)

    elif event_type == "activated":
        wa_msg = f"*[Service Activated] Order {order_num}*\\n\\nYour high-speed connection and digital services are now LIVE! Welcome to digital small business operations."
        sms_msg = f"Accel Business: Connection {order_num} is now active. High-speed internet is ready for use!"
        send_whatsapp(user_phone, wa_msg, order_id=order_num)
        send_sms(user_phone, sms_msg, order_id=order_num)
