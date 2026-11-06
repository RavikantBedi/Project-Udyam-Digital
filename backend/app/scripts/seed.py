"""Seed script — loads CSV data into SQL tables idempotently."""
import csv
import os
from datetime import datetime

from sqlmodel import Session, select

from app.core.config import get_data_dir, get_settings
from app.core.db import engine, init_db
from app.models.models import GstinRegistry, Lead, Order, Product, UdyamRegistry, User
from app.security.auth import hash_password

settings = get_settings()


def seed():
    init_db()
    DATA_DIR = get_data_dir()
    with Session(engine) as session:
        # --- Seed products from catalogue CSV ---
        if session.exec(select(Product)).first() is None:
            prod_path = os.path.join(DATA_DIR, "product_catalogue.csv")
            if os.path.exists(prod_path):
                count = 0
                with open(prod_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            p = Product(
                                product_id=row["product_id"],
                                name=row["product_name"],
                                category=row["category"],
                                price_min=float(row["price_min_inr_per_month"]),
                                price_max=float(row["price_max_inr_per_month"]),
                                one_time_setup=float(row.get("one_time_setup_inr") or 0),
                                min_contract_months=int(row.get("min_contract_months") or 12),
                                available_city_tiers=row.get("available_city_tiers", ""),
                                min_employees=int(row.get("min_employees") or 0),
                                min_sites=int(row.get("min_sites") or 1),
                                requires_gstin=row.get("requires_gstin", "N"),
                                requires_one_of=row.get("requires_one_of", ""),
                                typical_install_days=int(row.get("typical_install_days") or 3),
                                target_segments=row.get("target_segments", ""),
                            )
                            session.add(p)
                            count += 1
                        except Exception as e:
                            print(f"[seed] Product row error: {e}")
                            continue
                session.commit()
                print(f"[seed] {count} products loaded from {prod_path}")
            else:
                print(f"[seed] WARNING: product_catalogue.csv not found at {prod_path}")

        # --- Seed GSTIN registry ---
        if session.exec(select(GstinRegistry)).first() is None:
            gstin_path = os.path.join(DATA_DIR, "mock_gstin_registry.csv")
            if os.path.exists(gstin_path):
                count = 0
                with open(gstin_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            r = GstinRegistry(
                                gstin=row["gstin"],
                                legal_name=row.get("legal_name", ""),
                                trade_name=row.get("trade_name", ""),
                                constitution=row.get("constitution", ""),
                                principal_place_of_business=row.get("principal_place_of_business", ""),
                                state=row.get("state", ""),
                                registration_date=row.get("registration_date", ""),
                                status=row.get("status", ""),
                            )
                            session.add(r)
                            count += 1
                        except Exception:
                            continue
                session.commit()
                print(f"[seed] {count} GSTIN registry entries loaded")
            else:
                print("[seed] WARNING: mock_gstin_registry.csv not found")

        # --- Seed Udyam registry ---
        if session.exec(select(UdyamRegistry)).first() is None:
            udyam_path = os.path.join(DATA_DIR, "mock_udyam_registry.csv")
            if os.path.exists(udyam_path):
                count = 0
                with open(udyam_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            r = UdyamRegistry(
                                udyam_number=row["udyam_number"],
                                name=row.get("name", ""),
                                status=row.get("status", ""),
                            )
                            session.add(r)
                            count += 1
                        except Exception:
                            continue
                session.commit()
                print(f"[seed] {count} Udyam registry entries loaded")
            else:
                print("[seed] WARNING: mock_udyam_registry.csv not found")

        # --- Seed leads (first 500 for performance) ---
        if session.exec(select(Lead)).first() is None:
            lead_path = os.path.join(DATA_DIR, "smb_leads.csv")
            if os.path.exists(lead_path):
                count = 0
                with open(lead_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if count >= 500:
                            break
                        try:
                            lead = Lead(
                                lead_id=row["lead_id"],
                                business_name=row["business_name"],
                                business_type=row["business_type"],
                                segment=row["segment"],
                                city=row["city"],
                                city_tier=int(row["city_tier"]),
                                preferred_language=row["preferred_language"],
                                employee_count=int(row.get("employee_count") or 0),
                                num_sites=int(row.get("num_sites") or 1),
                                has_gstin=row["has_gstin"],
                                gstin=row.get("gstin", ""),
                                has_udyam=row["has_udyam"],
                                udyam_number=row.get("udyam_number", ""),
                                stage_reached=row["stage_reached"],
                                outcome=row.get("outcome", ""),
                                drop_reason=row.get("drop_reason", ""),
                                monthly_bundle_value_inr=float(row.get("monthly_bundle_value_inr") or 0),
                                lead_source=row.get("lead_source", ""),
                            )
                            session.add(lead)
                            count += 1
                        except Exception:
                            continue
                session.commit()
                print(f"[seed] {count} leads loaded")
            else:
                print(f"[seed] WARNING: smb_leads.csv not found at {lead_path}")

        # --- Seed demo order ---
        if session.exec(select(Order)).first() is None:
            demo_order = Order(
                order_id="ORD-DEMO0001",
                lead_id="LEAD-0001",
                business_name="Dr. Priya Sharma Clinic",
                phone="98765•••••",
                status="KYC verified",
                bundle_json='["P02","P16","P07","P20","P17"]',
                monthly_total=4299.0,
                one_time_total=3500.0,
                language="hi",
                created_at=datetime(2026, 7, 15, 10, 30),
            )
            session.add(demo_order)
            session.commit()
            print("[seed] Demo order created: ORD-DEMO0001")

        # --- Seed roles (dev only) ---
        if settings.app_env == "dev":
            users_to_seed = [
                (settings.admin_email, settings.admin_password, "Accel Admin", "admin"),
                (settings.sales_email, settings.sales_password, "Sales Executive", "sales"),
                (settings.partner_email, settings.partner_password, "Channel Partner", "partner"),
            ]
            for email, password, business_name, role in users_to_seed:
                if session.exec(select(User).where(User.email == email)).first() is None:
                    user = User(
                        user_id=f"USR-{role.upper()}-0001",
                        email=email,
                        phone="9999999999",
                        business_name=business_name,
                        password_hash=hash_password(password),
                        password_algorithm="argon2id",
                        role=role,
                    )
                    session.add(user)
                    print(f"[seed] {role} user created: {email}")
            session.commit()

    print("[seed] Complete")


if __name__ == "__main__":
    seed()
