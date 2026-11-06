"""Initial migration

Revision ID: f22338f7c904
Revises: 
Create Date: 2026-11-06 06:04:27.628552+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f22338f7c904'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### products (catalogue) ###
    op.create_table(
        'product',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('price_min', sa.Float(), nullable=False),
        sa.Column('price_max', sa.Float(), nullable=False),
        sa.Column('one_time_setup', sa.Float(), nullable=False),
        sa.Column('min_contract_months', sa.Integer(), nullable=False),
        sa.Column('available_city_tiers', sa.String(), nullable=False),
        sa.Column('min_employees', sa.Integer(), nullable=True),
        sa.Column('min_sites', sa.Integer(), nullable=True),
        sa.Column('requires_gstin', sa.String(), nullable=True),
        sa.Column('requires_one_of', sa.String(), nullable=True),
        sa.Column('typical_install_days', sa.Integer(), nullable=True),
        sa.Column('target_segments', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id'),
    )
    op.create_index(op.f('ix_product_product_id'), 'product', ['product_id'], unique=True)

    # ### leads ###
    op.create_table(
        'lead',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.String(), nullable=False),
        sa.Column('business_name', sa.String(), nullable=False),
        sa.Column('business_type', sa.String(), nullable=False),
        sa.Column('segment', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('city_tier', sa.Integer(), nullable=False),
        sa.Column('preferred_language', sa.String(), nullable=False),
        sa.Column('employee_count', sa.Integer(), nullable=False),
        sa.Column('num_sites', sa.Integer(), nullable=False),
        sa.Column('has_gstin', sa.String(), nullable=False),
        sa.Column('gstin', sa.String(), nullable=True),
        sa.Column('has_udyam', sa.String(), nullable=False),
        sa.Column('udyam_number', sa.String(), nullable=True),
        sa.Column('stage_reached', sa.String(), nullable=False),
        sa.Column('outcome', sa.String(), nullable=True),
        sa.Column('drop_reason', sa.String(), nullable=True),
        sa.Column('monthly_bundle_value_inr', sa.Float(), nullable=True),
        sa.Column('lead_source', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lead_id'),
    )
    op.create_index(op.f('ix_lead_lead_id'), 'lead', ['lead_id'], unique=True)

    # ### orders ###
    op.create_table(
        'order',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('lead_id', sa.String(), nullable=True),
        sa.Column('business_name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('bundle_json', sa.String(), nullable=True),
        sa.Column('monthly_total', sa.Float(), nullable=True),
        sa.Column('one_time_total', sa.Float(), nullable=True),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('installed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
    )
    op.create_index(op.f('ix_order_order_id'), 'order', ['order_id'], unique=True)

    # ### consent ledger ###
    op.create_table(
        'consentledger',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('consent_given', sa.Boolean(), nullable=False),
        sa.Column('marketing_consent', sa.Boolean(), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('consent_hash', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ### users ###
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('business_name', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_user_id'), 'user', ['user_id'], unique=True)

    # ### notification log ###
    op.create_table(
        'notificationlog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('order_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ### GSTIN registry ###
    op.create_table(
        'gstin_registry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gstin', sa.String(), nullable=False),
        sa.Column('legal_name', sa.String(), nullable=True),
        sa.Column('trade_name', sa.String(), nullable=True),
        sa.Column('constitution', sa.String(), nullable=True),
        sa.Column('principal_place_of_business', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('registration_date', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gstin'),
    )
    op.create_index(op.f('ix_gstin_registry_gstin'), 'gstin_registry', ['gstin'], unique=True)

    # ### Udyam registry ###
    op.create_table(
        'udyam_registry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('udyam_number', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('udyam_number'),
    )
    op.create_index(op.f('ix_udyam_registry_udyam_number'), 'udyam_registry', ['udyam_number'], unique=True)

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### end Alembic commands ###
    op.drop_table('udyam_registry')
    op.drop_table('gstin_registry')
    op.drop_table('notificationlog')
    op.drop_table('user')
    op.drop_table('consentledger')
    op.drop_table('order')
    op.drop_table('lead')
    op.drop_table('product')
