import csv
import os
from sqlmodel import Session, select
from app.core.db import engine, init_db
from app.models.models import Product, Lead

DATA_DIR = os.getenv('DATA_DIR', '/data')
if not os.path.exists(DATA_DIR):
    DATA_DIR = '../data'
if not os.path.exists(DATA_DIR):
    DATA_DIR = './data'

def seed():
    init_db()
    with Session(engine) as session:
        # Products
        if session.exec(select(Product)).first() is None:
            prod_path = os.path.join(DATA_DIR, 'product_catalogue.csv')
            with open(prod_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    p = Product(
                        product_id=row['product_id'],
                        name=row['product_name'],
                        category=row['category'],
                        price_min=float(row['price_min_inr']),
                        price_max=float(row['price_max_inr']),
                        one_time_setup=float(row['one_time_setup_inr']),
                        min_contract_months=int(row['min_contract_months']),
                        available_city_tiers=row['available_city_tiers'],
                        min_employees=int(row['min_employees'] or 0),
                        min_sites=int(row['min_sites'] or 1),
                        requires_gstin=row['requires_gstin'],
                        requires_one_of=row['requires_one_of'],
                        typical_install_days=int(row['typical_install_days']),
                        target_segments=row['target_segments'],
                    )
                    session.add(p)
            session.commit()
        # Leads (sample for back-office)
        if session.exec(select(Lead)).first() is None:
            lead_path = os.path.join(DATA_DIR, 'smb_leads.csv')
            count = 0
            with open(lead_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if count >= 500:  # seed first 500 for demo
                        break
                    l = Lead(
                        lead_id=row['lead_id'],
                        business_name=row['business_name'],
                        business_type=row['business_type'],
                        segment=row['segment'],
                        city=row['city'],
                        city_tier=int(row['city_tier']),
                        preferred_language=row['preferred_language'],
                        employee_count=int(row['employee_count']),
                        num_sites=int(row['num_sites']),
                        has_gstin=row['has_gstin'],
                        gstin=row['gstin'],
                        has_udyam=row['has_udyam'],
                        udyam_number=row['udyam_number'],
                        stage_reached=row['stage_reached'],
                        outcome=row['outcome'],
                        drop_reason=row['drop_reason'],
                        monthly_bundle_value_inr=float(row['monthly_bundle_value_inr'] or 0),
                        lead_source=row['lead_source'],
                    )
                    session.add(l)
                    count += 1
            session.commit()
        print('Seed complete')

if __name__ == '__main__':
    seed()
