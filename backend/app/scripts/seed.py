import csv
import os
from sqlmodel import Session, select
from app.core.db import engine, init_db
from app.models.models import Product, Lead, Order
from app.core.config import get_data_dir
from datetime import datetime


def seed():
    init_db()
    DATA_DIR = get_data_dir()
    with Session(engine) as session:
        # Seed products
        if session.exec(select(Product)).first() is None:
            prod_path = os.path.join(DATA_DIR, "product_catalogue.csv")
            if os.path.exists(prod_path):
                with open(prod_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        p = Product(
                            product_id=row["product_id"],
                            name=row["product_name"],
                            category=row["category"],
                            price_min=float(row["price_min_inr_per_month"]),
                            price_max=float(row["price_max_inr_per_month"]),
                            one_time_setup=float(row["one_time_setup_inr"]),
                            min_contract_months=int(row["min_contract_months"]),
                            available_city_tiers=row["available_city_tiers"],
                            min_employees=int(row.get("min_employees") or 0),
                            min_sites=int(row.get("min_sites") or 1),
                            requires_gstin=row["requires_gstin"],
                            requires_one_of=row["requires_one_of"],
                            typical_install_days=int(row["typical_install_days"]),
                            target_segments=row["target_segments"],
                        )
                        session.add(p)
                session.commit()
                print(f"[seed] Products loaded from {prod_path}")
            else:
                print(f"[seed] WARNING: product_catalogue.csv not found at {prod_path}")

        # Seed leads (first 500 for performance)
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
                            l = Lead(
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
                            session.add(l)
                            count += 1
                        except Exception as e:
                            print(f"[seed] Lead row error: {e}")
                            continue
                session.commit()
                print(f"[seed] {count} leads loaded")
            else:
                print(f"[seed] WARNING: smb_leads.csv not found at {lead_path}")

        # Seed a demo order if none exist
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

    print("[seed] Complete")


if __name__ == "__main__":
    seed()
