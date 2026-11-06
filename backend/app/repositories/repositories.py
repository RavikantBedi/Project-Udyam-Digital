"""Repository layer — all direct database access lives here."""

from sqlmodel import Session, select

from app.models.models import (
    ConsentLedger,
    GstinRegistry,
    Lead,
    NotificationLog,
    Order,
    Product,
    UdyamRegistry,
    User,
)


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> list[Product]:
        return self.session.exec(select(Product)).all()

    def get_by_id(self, product_id: str) -> Product | None:
        return self.session.exec(
            select(Product).where(Product.product_id == product_id)
        ).first()

    def create(self, product: Product) -> Product:
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def seed_if_empty(self, products: list[Product]) -> None:
        if self.session.exec(select(Product)).first() is None:
            for p in products:
                self.session.add(p)
            self.session.commit()


class LeadRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> list[Lead]:
        return self.session.exec(select(Lead)).all()

    def get_by_id(self, lead_id: str) -> Lead | None:
        return self.session.exec(
            select(Lead).where(Lead.lead_id == lead_id)
        ).first()

    def create(self, lead: Lead) -> Lead:
        self.session.add(lead)
        self.session.commit()
        self.session.refresh(lead)
        return lead

    def update_assignment(
        self, lead_id: str, assignee: str, assignee_type: str
    ) -> Lead | None:
        lead = self.get_by_id(lead_id)
        if not lead:
            return None
        # Store assignment in a lightweight way — extend Lead model if needed
        self.session.add(lead)
        self.session.commit()
        return lead

    def seed_if_empty(self, leads: list[Lead]) -> None:
        if self.session.exec(select(Lead)).first() is None:
            for lead in leads:
                self.session.add(lead)
            self.session.commit()


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, order_id: str) -> Order | None:
        return self.session.exec(
            select(Order).where(Order.order_id == order_id)
        ).first()

    def create(self, order: Order) -> Order:
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def update_status(self, order_id: str, status: str) -> Order | None:
        order = self.get_by_id(order_id)
        if not order:
            return None
        order.status = status
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def list_all(self) -> list[Order]:
        return self.session.exec(select(Order)).all()


class ConsentLedgerRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, ledger: ConsentLedger) -> ConsentLedger:
        self.session.add(ledger)
        self.session.commit()
        self.session.refresh(ledger)
        return ledger

    def list_for_order(self, order_id: str) -> list[ConsentLedger]:
        return self.session.exec(
            select(ConsentLedger).where(ConsentLedger.order_id == order_id)
        ).all()


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.exec(
            select(User).where(User.email == email)
        ).first()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def list_all(self) -> list[User]:
        return self.session.exec(select(User)).all()


class NotificationLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, log: NotificationLog) -> NotificationLog:
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_recent(
        self, channel: str | None = None, limit: int = 30
    ) -> list[NotificationLog]:
        query = select(NotificationLog).order_by(NotificationLog.created_at.desc())
        if channel:
            query = query.where(NotificationLog.channel == channel)
        return self.session.exec(query.limit(limit)).all()

    def list_for_order(self, order_id: str) -> list[NotificationLog]:
        return self.session.exec(
            select(NotificationLog)
            .where(
                (NotificationLog.order_id == order_id)
                | (NotificationLog.channel.in_(["whatsapp", "sms"]))
            )
            .order_by(NotificationLog.created_at.desc())
            .limit(10)
        ).all()


class GstinRegistryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_gstin(self, gstin: str) -> GstinRegistry | None:
        return self.session.exec(
            select(GstinRegistry).where(GstinRegistry.gstin == gstin)
        ).first()


class UdyamRegistryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_udyam(self, udyam_number: str) -> UdyamRegistry | None:
        return self.session.exec(
            select(UdyamRegistry).where(UdyamRegistry.udyam_number == udyam_number)
        ).first()
