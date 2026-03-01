from datetime import UTC, datetime, time, timedelta


def _aware(dt: datetime | None) -> datetime | None:
    """Ensure datetime is timezone-aware (handles pre-TIMESTAMPTZ databases)."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    Time,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship
from sqlalchemy.sql import func


class AwareDateTime(TypeDecorator):
    """DateTime that auto-converts naive values to UTC-aware on load from DB.

    Handles pre-TIMESTAMPTZ databases that return naive datetimes.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self):
        super().__init__(timezone=True)

    def process_result_value(self, value, dialect):
        if value is not None and isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


Base = declarative_base()


server_squad_promo_groups = Table(
    'server_squad_promo_groups',
    Base.metadata,
    Column(
        'server_squad_id',
        Integer,
        ForeignKey('server_squads.id', ondelete='CASCADE'),
        primary_key=True,
    ),
    Column(
        'promo_group_id',
        Integer,
        ForeignKey('promo_groups.id', ondelete='CASCADE'),
        primary_key=True,
    ),
)


# M2M С‚Р°Р±Р»РёС†Р° РґР»СЏ СЃРІСЏР·Рё С‚Р°СЂРёС„РѕРІ СЃ РїСЂРѕРјРѕРіСЂСѓРїРїР°РјРё (РґРѕСЃС‚СѓРї Рє С‚Р°СЂРёС„Сѓ)
tariff_promo_groups = Table(
    'tariff_promo_groups',
    Base.metadata,
    Column(
        'tariff_id',
        Integer,
        ForeignKey('tariffs.id', ondelete='CASCADE'),
        primary_key=True,
    ),
    Column(
        'promo_group_id',
        Integer,
        ForeignKey('promo_groups.id', ondelete='CASCADE'),
        primary_key=True,
    ),
)


# M2M С‚Р°Р±Р»РёС†Р° РґР»СЏ СЃРІСЏР·Рё РїР»Р°С‚С‘Р¶РЅС‹С… РјРµС‚РѕРґРѕРІ СЃ РїСЂРѕРјРѕРіСЂСѓРїРїР°РјРё (СѓСЃР»РѕРІРёСЏ РїРѕРєР°Р·Р°)
payment_method_promo_groups = Table(
    'payment_method_promo_groups',
    Base.metadata,
    Column(
        'payment_method_config_id',
        Integer,
        ForeignKey('payment_method_configs.id', ondelete='CASCADE'),
        primary_key=True,
    ),
    Column(
        'promo_group_id',
        Integer,
        ForeignKey('promo_groups.id', ondelete='CASCADE'),
        primary_key=True,
    ),
)


class UserStatus(Enum):
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    DELETED = 'deleted'


class SubscriptionStatus(Enum):
    TRIAL = 'trial'
    ACTIVE = 'active'
    EXPIRED = 'expired'
    DISABLED = 'disabled'
    PENDING = 'pending'


class TransactionType(Enum):
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    SUBSCRIPTION_PAYMENT = 'subscription_payment'
    REFUND = 'refund'
    REFERRAL_REWARD = 'referral_reward'
    POLL_REWARD = 'poll_reward'


class PromoCodeType(Enum):
    BALANCE = 'balance'
    SUBSCRIPTION_DAYS = 'subscription_days'
    TRIAL_SUBSCRIPTION = 'trial_subscription'
    PROMO_GROUP = 'promo_group'
    DISCOUNT = 'discount'  # РћРґРЅРѕСЂР°Р·РѕРІР°СЏ РїСЂРѕС†РµРЅС‚РЅР°СЏ СЃРєРёРґРєР° (balance_bonus_kopeks = РїСЂРѕС†РµРЅС‚, subscription_days = С‡Р°СЃС‹)


class PaymentMethod(Enum):
    TELEGRAM_STARS = 'telegram_stars'
    TRIBUTE = 'tribute'
    YOOKASSA = 'yookassa'
    CRYPTOBOT = 'cryptobot'
    HELEKET = 'heleket'
    MULENPAY = 'mulenpay'
    PAL24 = 'pal24'
    WATA = 'wata'
    PLATEGA = 'platega'
    CLOUDPAYMENTS = 'cloudpayments'
    FREEKASSA = 'freekassa'
    KASSA_AI = 'kassa_ai'
    MANUAL = 'manual'
    BALANCE = 'balance'


class MainMenuButtonActionType(Enum):
    URL = 'url'
    MINI_APP = 'mini_app'


class MainMenuButtonVisibility(Enum):
    ALL = 'all'
    ADMINS = 'admins'
    SUBSCRIBERS = 'subscribers'


class WheelPrizeType(Enum):
    """РўРёРїС‹ РїСЂРёР·РѕРІ РЅР° РєРѕР»РµСЃРµ СѓРґР°С‡Рё."""

    SUBSCRIPTION_DAYS = 'subscription_days'
    BALANCE_BONUS = 'balance_bonus'
    TRAFFIC_GB = 'traffic_gb'
    PROMOCODE = 'promocode'
    NOTHING = 'nothing'


class WheelSpinPaymentType(Enum):
    """РЎРїРѕСЃРѕР±С‹ РѕРїР»Р°С‚С‹ СЃРїРёРЅР° РєРѕР»РµСЃР°."""

    TELEGRAM_STARS = 'telegram_stars'
    SUBSCRIPTION_DAYS = 'subscription_days'


class YooKassaPayment(Base):
    __tablename__ = 'yookassa_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    yookassa_payment_id = Column(String(255), unique=True, nullable=False, index=True)
    amount_kopeks = Column(Integer, nullable=False)
    currency = Column(String(3), default='RUB', nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    is_paid = Column(Boolean, default=False)
    is_captured = Column(Boolean, default=False)
    confirmation_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    payment_method_type = Column(String(50), nullable=True)
    refundable = Column(Boolean, default=False)
    test_mode = Column(Boolean, default=False)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())
    yookassa_created_at = Column(AwareDateTime(), nullable=True)
    captured_at = Column(AwareDateTime(), nullable=True)
    user = relationship('User', backref='yookassa_payments')
    transaction = relationship('Transaction', backref='yookassa_payment')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100

    @property
    def is_pending(self) -> bool:
        return self.status == 'pending'

    @property
    def is_succeeded(self) -> bool:
        return self.status == 'succeeded' and self.is_paid

    @property
    def is_failed(self) -> bool:
        return self.status in ['canceled', 'failed']

    @property
    def can_be_captured(self) -> bool:
        return self.status == 'waiting_for_capture'

    def __repr__(self):
        return f'<YooKassaPayment(id={self.id}, yookassa_id={self.yookassa_payment_id}, amount={self.amount_rubles}в‚Ѕ, status={self.status})>'


class CryptoBotPayment(Base):
    __tablename__ = 'cryptobot_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    invoice_id = Column(String(255), unique=True, nullable=False, index=True)
    amount = Column(String(50), nullable=False)
    asset = Column(String(10), nullable=False)

    status = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    payload = Column(Text, nullable=True)

    bot_invoice_url = Column(Text, nullable=True)
    mini_app_invoice_url = Column(Text, nullable=True)
    web_app_invoice_url = Column(Text, nullable=True)

    paid_at = Column(AwareDateTime(), nullable=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', backref='cryptobot_payments')
    transaction = relationship('Transaction', backref='cryptobot_payment')

    @property
    def amount_float(self) -> float:
        try:
            return float(self.amount)
        except (ValueError, TypeError):
            return 0.0

    @property
    def is_paid(self) -> bool:
        return self.status == 'paid'

    @property
    def is_pending(self) -> bool:
        return self.status == 'active'

    @property
    def is_expired(self) -> bool:
        return self.status == 'expired'

    def __repr__(self):
        return f'<CryptoBotPayment(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount} {self.asset}, status={self.status})>'


class HeleketPayment(Base):
    __tablename__ = 'heleket_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    uuid = Column(String(255), unique=True, nullable=False, index=True)
    order_id = Column(String(128), unique=True, nullable=False, index=True)

    amount = Column(String(50), nullable=False)
    currency = Column(String(10), nullable=False)
    payer_amount = Column(String(50), nullable=True)
    payer_currency = Column(String(10), nullable=True)
    exchange_rate = Column(Float, nullable=True)
    discount_percent = Column(Integer, nullable=True)

    status = Column(String(50), nullable=False)
    payment_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    paid_at = Column(AwareDateTime(), nullable=True)
    expires_at = Column(AwareDateTime(), nullable=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', backref='heleket_payments')
    transaction = relationship('Transaction', backref='heleket_payment')

    @property
    def amount_float(self) -> float:
        try:
            return float(self.amount)
        except (TypeError, ValueError):
            return 0.0

    @property
    def amount_kopeks(self) -> int:
        return int(round(self.amount_float * 100))

    @property
    def payer_amount_float(self) -> float:
        try:
            return float(self.payer_amount) if self.payer_amount is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @property
    def is_paid(self) -> bool:
        return self.status in {'paid', 'paid_over'}

    def __repr__(self):
        return (
            f'<HeleketPayment(id={self.id}, uuid={self.uuid}, order_id={self.order_id}, amount={self.amount}'
            f' {self.currency}, status={self.status})>'
        )


class MulenPayPayment(Base):
    __tablename__ = 'mulenpay_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    mulen_payment_id = Column(Integer, nullable=True, index=True)
    uuid = Column(String(255), unique=True, nullable=False, index=True)
    amount_kopeks = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default='RUB')
    description = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default='created')
    is_paid = Column(Boolean, default=False)
    paid_at = Column(AwareDateTime(), nullable=True)

    payment_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    callback_payload = Column(JSON, nullable=True)

    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', backref='mulenpay_payments')
    transaction = relationship('Transaction', backref='mulenpay_payment')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f'<MulenPayPayment(id={self.id}, mulen_id={self.mulen_payment_id}, amount={self.amount_rubles}в‚Ѕ, status={self.status})>'


class Pal24Payment(Base):
    __tablename__ = 'pal24_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    bill_id = Column(String(255), unique=True, nullable=False, index=True)
    order_id = Column(String(255), nullable=True, index=True)
    amount_kopeks = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default='RUB')
    description = Column(Text, nullable=True)
    type = Column(String(20), nullable=False, default='normal')

    status = Column(String(50), nullable=False, default='NEW')
    is_active = Column(Boolean, default=True)
    is_paid = Column(Boolean, default=False)
    paid_at = Column(AwareDateTime(), nullable=True)
    last_status = Column(String(50), nullable=True)
    last_status_checked_at = Column(AwareDateTime(), nullable=True)

    link_url = Column(Text, nullable=True)
    link_page_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    callback_payload = Column(JSON, nullable=True)

    payment_id = Column(String(255), nullable=True, index=True)
    payment_status = Column(String(50), nullable=True)
    payment_method = Column(String(50), nullable=True)
    balance_amount = Column(String(50), nullable=True)
    balance_currency = Column(String(10), nullable=True)
    payer_account = Column(String(255), nullable=True)

    ttl = Column(Integer, nullable=True)
    expires_at = Column(AwareDateTime(), nullable=True)

    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', backref='pal24_payments')
    transaction = relationship('Transaction', backref='pal24_payment')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100

    @property
    def is_pending(self) -> bool:
        return self.status in {'NEW', 'PROCESS'}

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f'<Pal24Payment(id={self.id}, bill_id={self.bill_id}, amount={self.amount_rubles}в‚Ѕ, status={self.status})>'
        )


class WataPayment(Base):
    __tablename__ = 'wata_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    payment_link_id = Column(String(64), unique=True, nullable=False, index=True)
    order_id = Column(String(255), nullable=True, index=True)
    amount_kopeks = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default='RUB')
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)

    status = Column(String(50), nullable=False, default='Opened')
    is_paid = Column(Boolean, default=False)
    paid_at = Column(AwareDateTime(), nullable=True)
    last_status = Column(String(50), nullable=True)
    terminal_public_id = Column(String(64), nullable=True)

    url = Column(Text, nullable=True)
    success_redirect_url = Column(Text, nullable=True)
    fail_redirect_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    callback_payload = Column(JSON, nullable=True)

    expires_at = Column(AwareDateTime(), nullable=True)

    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', backref='wata_payments')
    transaction = relationship('Transaction', backref='wata_payment')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f'<WataPayment(id={self.id}, link_id={self.payment_link_id}, amount={self.amount_rubles}в‚Ѕ, status={self.status})>'


class PlategaPayment(Base):
    __tablename__ = 'platega_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    platega_transaction_id = Column(String(255), unique=True, nullable=True, index=True)
    correlation_id = Column(String(64), unique=True, nullable=False, index=True)
    amount_kopeks = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default='RUB')
    description = Column(Text, nullable=True)

    payment_method_code = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default='PENDING')
    is_paid = Column(Boolean, default=False)
    paid_at = Column(AwareDateTime(), nullable=True)

    redirect_url = Column(Text, nullable=True)
    return_url = Column(Text, nullable=True)
    failed_url = Column(Text, nullable=True)
    payload = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    callback_payload = Column(JSON, nullable=True)

    expires_at = Column(AwareDateTime(), nullable=True)

    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', backref='platega_payments')
    transaction = relationship('Transaction', backref='platega_payment')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f'<PlategaPayment(id={self.id}, transaction_id={self.platega_transaction_id}, amount={self.amount_rubles}в‚Ѕ, status={self.status}, method={self.payment_method_code})>'


class CloudPaymentsPayment(Base):
    __tablename__ = 'cloudpayments_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # CloudPayments РёРґРµРЅС‚РёС„РёРєР°С‚РѕСЂС‹
    transaction_id_cp = Column(BigInteger, unique=True, nullable=True, index=True)  # TransactionId РѕС‚ CloudPayments
    invoice_id = Column(String(255), unique=True, nullable=False, index=True)  # РќР°С€ InvoiceId

    amount_kopeks = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default='RUB')
    description = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default='pending')  # pending, completed, failed, authorized
    is_paid = Column(Boolean, default=False)
    paid_at = Column(AwareDateTime(), nullable=True)

    # Р”Р°РЅРЅС‹Рµ РєР°СЂС‚С‹ (РјР°СЃРєРёСЂРѕРІР°РЅРЅС‹Рµ)
    card_first_six = Column(String(6), nullable=True)
    card_last_four = Column(String(4), nullable=True)
    card_type = Column(String(50), nullable=True)  # Visa, MasterCard, etc.
    card_exp_date = Column(String(10), nullable=True)  # MM/YY

    # РўРѕРєРµРЅ РґР»СЏ СЂРµРєСѓСЂСЂРµРЅС‚РЅС‹С… РїР»Р°С‚РµР¶РµР№
    token = Column(String(255), nullable=True)

    # URL РґР»СЏ РѕРїР»Р°С‚С‹ (РІРёРґР¶РµС‚)
    payment_url = Column(Text, nullable=True)

    # Email РїР»Р°С‚РµР»СЊС‰РёРєР°
    email = Column(String(255), nullable=True)

    # РўРµСЃС‚РѕРІС‹Р№ СЂРµР¶РёРј
    test_mode = Column(Boolean, default=False)

    # Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РґР°РЅРЅС‹Рµ
    metadata_json = Column(JSON, nullable=True)
    callback_payload = Column(JSON, nullable=True)

    # РЎРІСЏР·СЊ СЃ С‚СЂР°РЅР·Р°РєС†РёРµР№ РІ РЅР°С€РµР№ СЃРёСЃС‚РµРјРµ
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', backref='cloudpayments_payments')
    transaction = relationship('Transaction', backref='cloudpayments_payment')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100

    @property
    def is_pending(self) -> bool:
        return self.status == 'pending'

    @property
    def is_completed(self) -> bool:
        return self.status == 'completed' and self.is_paid

    @property
    def is_failed(self) -> bool:
        return self.status == 'failed'

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f'<CloudPaymentsPayment(id={self.id}, invoice={self.invoice_id}, amount={self.amount_rubles}в‚Ѕ, status={self.status})>'


class FreekassaPayment(Base):
    __tablename__ = 'freekassa_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # РРґРµРЅС‚РёС„РёРєР°С‚РѕСЂС‹
    order_id = Column(String(64), unique=True, nullable=False, index=True)  # РќР°С€ ID Р·Р°РєР°Р·Р°
    freekassa_order_id = Column(String(64), unique=True, nullable=True, index=True)  # intid РѕС‚ Freekassa

    # РЎСѓРјРјС‹
    amount_kopeks = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default='RUB')
    description = Column(Text, nullable=True)

    # РЎС‚Р°С‚СѓСЃС‹
    status = Column(String(32), nullable=False, default='pending')  # pending, success, failed, expired
    is_paid = Column(Boolean, default=False)

    # Р”Р°РЅРЅС‹Рµ РїР»Р°С‚РµР¶Р°
    payment_url = Column(Text, nullable=True)
    payment_system_id = Column(Integer, nullable=True)  # ID РїР»Р°С‚РµР¶РЅРѕР№ СЃРёСЃС‚РµРјС‹ FK

    # РњРµС‚Р°РґР°РЅРЅС‹Рµ
    metadata_json = Column(JSON, nullable=True)
    callback_payload = Column(JSON, nullable=True)

    # Р’СЂРµРјРµРЅРЅС‹Рµ РјРµС‚РєРё
    paid_at = Column(AwareDateTime(), nullable=True)
    expires_at = Column(AwareDateTime(), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    # РЎРІСЏР·СЊ СЃ С‚СЂР°РЅР·Р°РєС†РёРµР№
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    # Relationships
    user = relationship('User', backref='freekassa_payments')
    transaction = relationship('Transaction', backref='freekassa_payment')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100

    @property
    def is_pending(self) -> bool:
        return self.status == 'pending'

    @property
    def is_success(self) -> bool:
        return self.status == 'success' and self.is_paid

    @property
    def is_failed(self) -> bool:
        return self.status in ['failed', 'expired']

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f'<FreekassaPayment(id={self.id}, order_id={self.order_id}, amount={self.amount_rubles}в‚Ѕ, status={self.status})>'


class KassaAiPayment(Base):
    """РџР»Р°С‚РµР¶Рё С‡РµСЂРµР· KassaAI (api.fk.life)."""

    __tablename__ = 'kassa_ai_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # РРґРµРЅС‚РёС„РёРєР°С‚РѕСЂС‹
    order_id = Column(String(64), unique=True, nullable=False, index=True)  # РќР°С€ ID Р·Р°РєР°Р·Р°
    kassa_ai_order_id = Column(String(64), unique=True, nullable=True, index=True)  # orderId РѕС‚ KassaAI

    # РЎСѓРјРјС‹
    amount_kopeks = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default='RUB')
    description = Column(Text, nullable=True)

    # РЎС‚Р°С‚СѓСЃС‹
    status = Column(String(32), nullable=False, default='pending')  # pending, success, failed, expired
    is_paid = Column(Boolean, default=False)

    # Р”Р°РЅРЅС‹Рµ РїР»Р°С‚РµР¶Р°
    payment_url = Column(Text, nullable=True)
    payment_system_id = Column(Integer, nullable=True)  # ID РїР»Р°С‚РµР¶РЅРѕР№ СЃРёСЃС‚РµРјС‹ (44=РЎР‘Рџ, 36=РљР°СЂС‚С‹, 43=SberPay)

    # РњРµС‚Р°РґР°РЅРЅС‹Рµ
    metadata_json = Column(JSON, nullable=True)
    callback_payload = Column(JSON, nullable=True)

    # Р’СЂРµРјРµРЅРЅС‹Рµ РјРµС‚РєРё
    paid_at = Column(AwareDateTime(), nullable=True)
    expires_at = Column(AwareDateTime(), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    # РЎРІСЏР·СЊ СЃ С‚СЂР°РЅР·Р°РєС†РёРµР№
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)

    # Relationships
    user = relationship('User', backref='kassa_ai_payments')
    transaction = relationship('Transaction', backref='kassa_ai_payment')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100

    @property
    def is_pending(self) -> bool:
        return self.status == 'pending'

    @property
    def is_success(self) -> bool:
        return self.status == 'success' and self.is_paid

    @property
    def is_failed(self) -> bool:
        return self.status in ['failed', 'expired']

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f'<KassaAiPayment(id={self.id}, order_id={self.order_id}, amount={self.amount_rubles}в‚Ѕ, status={self.status})>'


class PromoGroup(Base):
    __tablename__ = 'promo_groups'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    priority = Column(Integer, nullable=False, default=0, index=True)
    server_discount_percent = Column(Integer, nullable=False, default=0)
    traffic_discount_percent = Column(Integer, nullable=False, default=0)
    device_discount_percent = Column(Integer, nullable=False, default=0)
    period_discounts = Column(JSON, nullable=True, default=dict)
    auto_assign_total_spent_kopeks = Column(Integer, nullable=True, default=None)
    apply_discounts_to_addons = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    users = relationship('User', back_populates='promo_group')
    user_promo_groups = relationship('UserPromoGroup', back_populates='promo_group', cascade='all, delete-orphan')
    server_squads = relationship(
        'ServerSquad',
        secondary=server_squad_promo_groups,
        back_populates='allowed_promo_groups',
        lazy='selectin',
    )

    def _get_period_discounts_map(self) -> dict[int, int]:
        raw_discounts = self.period_discounts or {}

        if isinstance(raw_discounts, dict):
            items = raw_discounts.items()
        else:
            items = []

        normalized: dict[int, int] = {}

        for key, value in items:
            try:
                period = int(key)
                percent = int(value)
            except (TypeError, ValueError):
                continue

            normalized[period] = max(0, min(100, percent))

        return normalized

    def _get_period_discount(self, period_days: int | None) -> int:
        if not period_days:
            return 0

        discounts = self._get_period_discounts_map()

        if period_days in discounts:
            return discounts[period_days]

        if self.is_default:
            try:
                from app.config import settings

                if settings.is_base_promo_group_period_discount_enabled():
                    config_discounts = settings.get_base_promo_group_period_discounts()
                    return config_discounts.get(period_days, 0)
            except Exception:
                return 0

        return 0

    def get_discount_percent(self, category: str, period_days: int | None = None) -> int:
        if category == 'period':
            return max(0, min(100, self._get_period_discount(period_days)))

        mapping = {
            'servers': self.server_discount_percent,
            'traffic': self.traffic_discount_percent,
            'devices': self.device_discount_percent,
        }
        percent = mapping.get(category) or 0

        if percent == 0 and self.is_default:
            base_period_discount = self._get_period_discount(period_days)
            percent = max(percent, base_period_discount)

        return max(0, min(100, percent))


class UserPromoGroup(Base):
    """РўР°Р±Р»РёС†Р° СЃРІСЏР·Рё Many-to-Many РјРµР¶РґСѓ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРјРё Рё РїСЂРѕРјРѕРіСЂСѓРїРїР°РјРё."""

    __tablename__ = 'user_promo_groups'

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    promo_group_id = Column(Integer, ForeignKey('promo_groups.id', ondelete='CASCADE'), primary_key=True)
    assigned_at = Column(AwareDateTime(), default=func.now())
    assigned_by = Column(String(50), default='system')

    user = relationship('User', back_populates='user_promo_groups')
    promo_group = relationship('PromoGroup', back_populates='user_promo_groups')

    def __repr__(self):
        return f"<UserPromoGroup(user_id={self.user_id}, promo_group_id={self.promo_group_id}, assigned_by='{self.assigned_by}')>"


class Tariff(Base):
    """РўР°СЂРёС„РЅС‹Р№ РїР»Р°РЅ РґР»СЏ СЂРµР¶РёРјР° РїСЂРѕРґР°Р¶ 'РўР°СЂРёС„С‹'."""

    __tablename__ = 'tariffs'

    id = Column(Integer, primary_key=True, index=True)

    # РћСЃРЅРѕРІРЅР°СЏ РёРЅС„РѕСЂРјР°С†РёСЏ
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # РџР°СЂР°РјРµС‚СЂС‹ С‚Р°СЂРёС„Р°
    traffic_limit_gb = Column(Integer, nullable=False, default=100)  # 0 = Р±РµР·Р»РёРјРёС‚
    device_limit = Column(Integer, nullable=False, default=1)
    device_price_kopeks = Column(
        Integer, nullable=True, default=None
    )  # Р¦РµРЅР° Р·Р° РґРѕРї. СѓСЃС‚СЂРѕР№СЃС‚РІРѕ (None = РЅРµР»СЊР·СЏ РґРѕРєСѓРїРёС‚СЊ)
    max_device_limit = Column(Integer, nullable=True, default=None)  # РњР°РєСЃ. СѓСЃС‚СЂРѕР№СЃС‚РІ (None = Р±РµР· РѕРіСЂР°РЅРёС‡РµРЅРёР№)

    # РЎРєРІР°РґС‹ (СЃРµСЂРІРµСЂС‹) РґРѕСЃС‚СѓРїРЅС‹Рµ РІ С‚Р°СЂРёС„Рµ
    allowed_squads = Column(JSON, default=list)  # СЃРїРёСЃРѕРє UUID СЃРєРІР°РґРѕРІ

    # Р›РёРјРёС‚С‹ С‚СЂР°С„РёРєР° РїРѕ СЃРµСЂРІРµСЂР°Рј (JSON: {"uuid": {"traffic_limit_gb": 100}, ...})
    # Р•СЃР»Рё СЃРµСЂРІРµСЂ РЅРµ СѓРєР°Р·Р°РЅ - РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РѕР±С‰РёР№ traffic_limit_gb
    server_traffic_limits = Column(JSON, default=dict)

    # Р¦РµРЅС‹ РЅР° РїРµСЂРёРѕРґС‹ РІ РєРѕРїРµР№РєР°С… (JSON: {"14": 30000, "30": 50000, "90": 120000, ...})
    period_prices = Column(JSON, nullable=False, default=dict)

    # РЈСЂРѕРІРµРЅСЊ С‚Р°СЂРёС„Р° (РґР»СЏ РІРёР·СѓР°Р»СЊРЅРѕРіРѕ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ, 1 = Р±Р°Р·РѕРІС‹Р№)
    tier_level = Column(Integer, default=1, nullable=False)

    # Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё
    is_trial_available = Column(Boolean, default=False, nullable=False)  # РњРѕР¶РЅРѕ Р»Рё РІР·СЏС‚СЊ С‚СЂРёР°Р» РЅР° СЌС‚РѕРј С‚Р°СЂРёС„Рµ
    allow_traffic_topup = Column(Boolean, default=True, nullable=False)
    family_enabled = Column(Boolean, default=False, nullable=False)
    family_max_members = Column(Integer, default=0, nullable=False)

    # Р”РѕРєСѓРїРєР° С‚СЂР°С„РёРєР°
    traffic_topup_enabled = Column(Boolean, default=False, nullable=False)  # Р Р°Р·СЂРµС€РµРЅР° Р»Рё РґРѕРєСѓРїРєР° С‚СЂР°С„РёРєР°
    # РџР°РєРµС‚С‹ С‚СЂР°С„РёРєР°: JSON {"5": 5000, "10": 9000, "20": 15000} (Р“Р‘: С†РµРЅР° РІ РєРѕРїРµР№РєР°С…)
    traffic_topup_packages = Column(JSON, default=dict)
    # РњР°РєСЃРёРјР°Р»СЊРЅС‹Р№ Р»РёРјРёС‚ С‚СЂР°С„РёРєР° РїРѕСЃР»Рµ РґРѕРєСѓРїРєРё (0 = Р±РµР· РѕРіСЂР°РЅРёС‡РµРЅРёР№)
    max_topup_traffic_gb = Column(Integer, default=0, nullable=False)

    # РЎСѓС‚РѕС‡РЅС‹Р№ С‚Р°СЂРёС„ - РµР¶РµРґРЅРµРІРЅРѕРµ СЃРїРёСЃР°РЅРёРµ
    is_daily = Column(Boolean, default=False, nullable=False)  # РЇРІР»СЏРµС‚СЃСЏ Р»Рё С‚Р°СЂРёС„ СЃСѓС‚РѕС‡РЅС‹Рј
    daily_price_kopeks = Column(Integer, default=0, nullable=False)  # Р¦РµРЅР° Р·Р° РґРµРЅСЊ РІ РєРѕРїРµР№РєР°С…

    # РџСЂРѕРёР·РІРѕР»СЊРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РґРЅРµР№
    custom_days_enabled = Column(Boolean, default=False, nullable=False)  # Р Р°Р·СЂРµС€РёС‚СЊ РїСЂРѕРёР·РІРѕР»СЊРЅРѕРµ РєРѕР»-РІРѕ РґРЅРµР№
    price_per_day_kopeks = Column(Integer, default=0, nullable=False)  # Р¦РµРЅР° Р·Р° 1 РґРµРЅСЊ РІ РєРѕРїРµР№РєР°С…
    min_days = Column(Integer, default=1, nullable=False)  # РњРёРЅРёРјР°Р»СЊРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РґРЅРµР№
    max_days = Column(Integer, default=365, nullable=False)  # РњР°РєСЃРёРјР°Р»СЊРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РґРЅРµР№

    # РџСЂРѕРёР·РІРѕР»СЊРЅС‹Р№ С‚СЂР°С„РёРє РїСЂРё РїРѕРєСѓРїРєРµ
    custom_traffic_enabled = Column(Boolean, default=False, nullable=False)  # Р Р°Р·СЂРµС€РёС‚СЊ РїСЂРѕРёР·РІРѕР»СЊРЅС‹Р№ С‚СЂР°С„РёРє
    traffic_price_per_gb_kopeks = Column(Integer, default=0, nullable=False)  # Р¦РµРЅР° Р·Р° 1 Р“Р‘ РІ РєРѕРїРµР№РєР°С…
    min_traffic_gb = Column(Integer, default=1, nullable=False)  # РњРёРЅРёРјР°Р»СЊРЅС‹Р№ С‚СЂР°С„РёРє РІ Р“Р‘
    max_traffic_gb = Column(Integer, default=1000, nullable=False)  # РњР°РєСЃРёРјР°Р»СЊРЅС‹Р№ С‚СЂР°С„РёРє РІ Р“Р‘

    # Р РµР¶РёРј СЃР±СЂРѕСЃР° С‚СЂР°С„РёРєР°: DAY, WEEK, MONTH, NO_RESET (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ Р±РµСЂС‘С‚СЃСЏ РёР· РєРѕРЅС„РёРіР°)
    traffic_reset_mode = Column(String(20), nullable=True, default=None)  # None = РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ РіР»РѕР±Р°Р»СЊРЅСѓСЋ РЅР°СЃС‚СЂРѕР№РєСѓ

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    # M2M СЃРІСЏР·СЊ СЃ РїСЂРѕРјРѕРіСЂСѓРїРїР°РјРё (РєР°РєРёРµ РїСЂРѕРјРѕРіСЂСѓРїРїС‹ РёРјРµСЋС‚ РґРѕСЃС‚СѓРї Рє С‚Р°СЂРёС„Сѓ)
    allowed_promo_groups = relationship(
        'PromoGroup',
        secondary=tariff_promo_groups,
        lazy='selectin',
    )

    # РџРѕРґРїРёСЃРєРё РЅР° СЌС‚РѕРј С‚Р°СЂРёС„Рµ
    subscriptions = relationship('Subscription', back_populates='tariff')

    @property
    def is_unlimited_traffic(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, Р±РµР·Р»РёРјРёС‚РЅС‹Р№ Р»Рё С‚СЂР°С„РёРє."""
        return self.traffic_limit_gb == 0

    def get_price_for_period(self, period_days: int) -> int | None:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ С†РµРЅСѓ РІ РєРѕРїРµР№РєР°С… РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ РїРµСЂРёРѕРґР°."""
        prices = self.period_prices or {}
        return prices.get(str(period_days))

    def get_available_periods(self) -> list[int]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РґРѕСЃС‚СѓРїРЅС‹С… РїРµСЂРёРѕРґРѕРІ РІ РґРЅСЏС…."""
        prices = self.period_prices or {}
        return sorted([int(p) for p in prices.keys()])

    def get_price_rubles(self, period_days: int) -> float | None:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ С†РµРЅСѓ РІ СЂСѓР±Р»СЏС… РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ РїРµСЂРёРѕРґР°."""
        price_kopeks = self.get_price_for_period(period_days)
        if price_kopeks is not None:
            return price_kopeks / 100
        return None

    def get_traffic_limit_for_server(self, squad_uuid: str) -> int:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ Р»РёРјРёС‚ С‚СЂР°С„РёРєР° РґР»СЏ РєРѕРЅРєСЂРµС‚РЅРѕРіРѕ СЃРµСЂРІРµСЂР°.

        Р•СЃР»Рё РґР»СЏ СЃРµСЂРІРµСЂР° РЅР°СЃС‚СЂРѕРµРЅ РѕС‚РґРµР»СЊРЅС‹Р№ Р»РёРјРёС‚ - РІРѕР·РІСЂР°С‰Р°РµС‚ РµРіРѕ,
        РёРЅР°С‡Рµ РІРѕР·РІСЂР°С‰Р°РµС‚ РѕР±С‰РёР№ traffic_limit_gb С‚Р°СЂРёС„Р°.
        """
        limits = self.server_traffic_limits or {}
        if squad_uuid in limits:
            server_limit = limits[squad_uuid]
            if isinstance(server_limit, dict) and 'traffic_limit_gb' in server_limit:
                return server_limit['traffic_limit_gb']
            if isinstance(server_limit, int):
                return server_limit
        return self.traffic_limit_gb

    def is_available_for_promo_group(self, promo_group_id: int | None) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, РґРѕСЃС‚СѓРїРµРЅ Р»Рё С‚Р°СЂРёС„ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕР№ РїСЂРѕРјРѕРіСЂСѓРїРїС‹."""
        if not self.allowed_promo_groups:
            return True  # Р•СЃР»Рё РЅРµС‚ РѕРіСЂР°РЅРёС‡РµРЅРёР№ - РґРѕСЃС‚СѓРїРµРЅ РІСЃРµРј
        if promo_group_id is None:
            return True  # Р•СЃР»Рё Сѓ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РЅРµС‚ РіСЂСѓРїРїС‹ - РґРѕСЃС‚СѓРїРµРЅ
        return any(pg.id == promo_group_id for pg in self.allowed_promo_groups)

    def get_traffic_topup_packages(self) -> dict[int, int]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїР°РєРµС‚С‹ С‚СЂР°С„РёРєР° РґР»СЏ РґРѕРєСѓРїРєРё: {Р“Р‘: С†РµРЅР° РІ РєРѕРїРµР№РєР°С…}."""
        packages = self.traffic_topup_packages or {}
        return {int(gb): int(price) for gb, price in packages.items()}

    def get_traffic_topup_price(self, gb: int) -> int | None:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ С†РµРЅСѓ РІ РєРѕРїРµР№РєР°С… РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ РїР°РєРµС‚Р° С‚СЂР°С„РёРєР°."""
        packages = self.get_traffic_topup_packages()
        return packages.get(gb)

    def get_available_traffic_packages(self) -> list[int]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РґРѕСЃС‚СѓРїРЅС‹С… РїР°РєРµС‚РѕРІ С‚СЂР°С„РёРєР° РІ Р“Р‘."""
        packages = self.get_traffic_topup_packages()
        return sorted(packages.keys())

    def can_topup_traffic(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, РјРѕР¶РЅРѕ Р»Рё РґРѕРєСѓРїРёС‚СЊ С‚СЂР°С„РёРє РЅР° СЌС‚РѕРј С‚Р°СЂРёС„Рµ."""
        return self.traffic_topup_enabled and bool(self.traffic_topup_packages) and not self.is_unlimited_traffic

    def get_daily_price_rubles(self) -> float:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃСѓС‚РѕС‡РЅСѓСЋ С†РµРЅСѓ РІ СЂСѓР±Р»СЏС…."""
        return self.daily_price_kopeks / 100 if self.daily_price_kopeks else 0

    def get_price_for_custom_days(self, days: int) -> int | None:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ С†РµРЅСѓ РґР»СЏ РїСЂРѕРёР·РІРѕР»СЊРЅРѕРіРѕ РєРѕР»РёС‡РµСЃС‚РІР° РґРЅРµР№."""
        if not self.custom_days_enabled or not self.price_per_day_kopeks:
            return None
        if days < self.min_days or days > self.max_days:
            return None
        return self.price_per_day_kopeks * days

    def get_price_for_custom_traffic(self, gb: int) -> int | None:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ С†РµРЅСѓ РґР»СЏ РїСЂРѕРёР·РІРѕР»СЊРЅРѕРіРѕ РєРѕР»РёС‡РµСЃС‚РІР° С‚СЂР°С„РёРєР°."""
        if not self.custom_traffic_enabled or not self.traffic_price_per_gb_kopeks:
            return None
        if gb < self.min_traffic_gb or gb > self.max_traffic_gb:
            return None
        return self.traffic_price_per_gb_kopeks * gb

    def can_purchase_custom_days(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, РјРѕР¶РЅРѕ Р»Рё РєСѓРїРёС‚СЊ РїСЂРѕРёР·РІРѕР»СЊРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РґРЅРµР№."""
        return self.custom_days_enabled and self.price_per_day_kopeks > 0

    def can_purchase_custom_traffic(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, РјРѕР¶РЅРѕ Р»Рё РєСѓРїРёС‚СЊ РїСЂРѕРёР·РІРѕР»СЊРЅС‹Р№ С‚СЂР°С„РёРє."""
        return self.custom_traffic_enabled and self.traffic_price_per_gb_kopeks > 0

    def __repr__(self):
        return f"<Tariff(id={self.id}, name='{self.name}', tier={self.tier_level}, active={self.is_active})>"


class PartnerStatus(Enum):
    """РЎС‚Р°С‚СѓСЃС‹ РїР°СЂС‚РЅС‘СЂСЃРєРѕРіРѕ Р°РєРєР°СѓРЅС‚Р°."""

    NONE = 'none'  # РќРµ РїРѕРґР°РІР°Р» Р·Р°СЏРІРєСѓ
    PENDING = 'pending'  # Р—Р°СЏРІРєР° РЅР° СЂР°СЃСЃРјРѕС‚СЂРµРЅРёРё
    APPROVED = 'approved'  # РџР°СЂС‚РЅС‘СЂ РѕРґРѕР±СЂРµРЅ
    REJECTED = 'rejected'  # Р—Р°СЏРІРєР° РѕС‚РєР»РѕРЅРµРЅР°


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)  # Nullable РґР»СЏ email-only РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№
    auth_type = Column(String(20), default='telegram', nullable=False)  # "telegram" РёР»Рё "email"
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    status = Column(String(20), default=UserStatus.ACTIVE.value)
    language = Column(String(5), default='ru')
    balance_kopeks = Column(Integer, default=0)
    used_promocodes = Column(Integer, default=0)
    has_had_paid_subscription = Column(Boolean, default=False, nullable=False)
    referred_by_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    referral_code = Column(String(20), unique=True, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())
    last_activity = Column(AwareDateTime(), default=func.now())
    remnawave_uuid = Column(String(255), nullable=True, unique=True)

    # Cabinet authentication fields
    email = Column(String(255), unique=True, nullable=True, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(AwareDateTime(), nullable=True)
    password_hash = Column(String(255), nullable=True)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(AwareDateTime(), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(AwareDateTime(), nullable=True)
    cabinet_last_login = Column(AwareDateTime(), nullable=True)
    # Email change fields
    email_change_new = Column(String(255), nullable=True)  # New email pending verification
    email_change_code = Column(String(6), nullable=True)  # 6-digit verification code
    email_change_expires = Column(AwareDateTime(), nullable=True)  # Code expiration
    # OAuth provider IDs
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    yandex_id = Column(String(255), unique=True, nullable=True, index=True)
    discord_id = Column(String(255), unique=True, nullable=True, index=True)
    vk_id = Column(BigInteger, unique=True, nullable=True, index=True)
    broadcasts = relationship('BroadcastHistory', back_populates='admin')
    referrals = relationship('User', backref='referrer', remote_side=[id], foreign_keys='User.referred_by_id')
    subscription = relationship('Subscription', back_populates='user', uselist=False)
    transactions = relationship('Transaction', back_populates='user')
    referral_earnings = relationship('ReferralEarning', foreign_keys='ReferralEarning.user_id', back_populates='user')
    discount_offers = relationship('DiscountOffer', back_populates='user')
    promo_offer_logs = relationship('PromoOfferLog', back_populates='user')
    lifetime_used_traffic_bytes = Column(BigInteger, default=0)
    auto_promo_group_assigned = Column(Boolean, nullable=False, default=False)
    auto_promo_group_threshold_kopeks = Column(BigInteger, nullable=False, default=0)
    referral_commission_percent = Column(Integer, nullable=True)
    promo_offer_discount_percent = Column(Integer, nullable=False, default=0)
    promo_offer_discount_source = Column(String(100), nullable=True)
    promo_offer_discount_expires_at = Column(AwareDateTime(), nullable=True)
    last_remnawave_sync = Column(AwareDateTime(), nullable=True)
    trojan_password = Column(String(255), nullable=True)
    vless_uuid = Column(String(255), nullable=True)
    ss_password = Column(String(255), nullable=True)
    has_made_first_topup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    promo_group_id = Column(Integer, ForeignKey('promo_groups.id', ondelete='RESTRICT'), nullable=True, index=True)
    promo_group = relationship('PromoGroup', back_populates='users')
    user_promo_groups = relationship('UserPromoGroup', back_populates='user', cascade='all, delete-orphan')
    poll_responses = relationship('PollResponse', back_populates='user')
    admin_roles_rel = relationship('UserRole', foreign_keys='[UserRole.user_id]', back_populates='user')
    notification_settings = Column(JSON, nullable=True, default=dict)
    last_pinned_message_id = Column(Integer, nullable=True)
    owned_family_group = relationship('FamilyGroup', back_populates='owner', uselist=False)
    family_memberships = relationship('FamilyMember', foreign_keys='[FamilyMember.user_id]', back_populates='user')
    sent_family_invites = relationship('FamilyInvite', foreign_keys='[FamilyInvite.inviter_user_id]', back_populates='inviter')
    received_family_invites = relationship('FamilyInvite', foreign_keys='[FamilyInvite.invitee_user_id]', back_populates='invitee')

    # РћРіСЂР°РЅРёС‡РµРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    restriction_topup = Column(Boolean, default=False, nullable=False)  # Р—Р°РїСЂРµС‚ РїРѕРїРѕР»РЅРµРЅРёСЏ
    restriction_subscription = Column(Boolean, default=False, nullable=False)  # Р—Р°РїСЂРµС‚ РїСЂРѕРґР»РµРЅРёСЏ/РїРѕРєСѓРїРєРё
    restriction_reason = Column(String(500), nullable=True)  # РџСЂРёС‡РёРЅР° РѕРіСЂР°РЅРёС‡РµРЅРёСЏ

    # РџР°СЂС‚РЅС‘СЂСЃРєР°СЏ СЃРёСЃС‚РµРјР°
    partner_status = Column(String(20), default=PartnerStatus.NONE.value, nullable=False, index=True)

    @property
    def is_partner(self) -> bool:
        """РџСЂРѕРІРµСЂРёС‚СЊ, СЏРІР»СЏРµС‚СЃСЏ Р»Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ РѕРґРѕР±СЂРµРЅРЅС‹Рј РїР°СЂС‚РЅС‘СЂРѕРј."""
        return self.partner_status == PartnerStatus.APPROVED.value

    @property
    def has_restrictions(self) -> bool:
        """РџСЂРѕРІРµСЂРёС‚СЊ, РµСЃС‚СЊ Р»Рё Сѓ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ Р°РєС‚РёРІРЅС‹Рµ РѕРіСЂР°РЅРёС‡РµРЅРёСЏ."""
        return self.restriction_topup or self.restriction_subscription

    @property
    def balance_rubles(self) -> float:
        return self.balance_kopeks / 100

    @property
    def full_name(self) -> str:
        """РџРѕР»РЅРѕРµ РёРјСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ СЃ РїРѕРґРґРµСЂР¶РєРѕР№ email-only СЋР·РµСЂРѕРІ."""
        parts = [self.first_name, self.last_name]
        name = ' '.join(filter(None, parts))
        if name:
            return name
        if self.username:
            return self.username
        if self.telegram_id:
            return f'ID{self.telegram_id}'
        if self.email:
            return self.email.split('@')[0]
        return f'User{self.id}'

    @property
    def is_email_user(self) -> bool:
        """РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅ С‡РµСЂРµР· email (Р±РµР· Telegram)."""
        return self.auth_type == 'email' and self.telegram_id is None

    @property
    def is_web_user(self) -> bool:
        """РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ Р±РµР· Telegram (email, OAuth Рё С‚.Рґ.)."""
        return self.telegram_id is None

    def get_primary_promo_group(self):
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїСЂРѕРјРѕРіСЂСѓРїРїСѓ СЃ РјР°РєСЃРёРјР°Р»СЊРЅС‹Рј РїСЂРёРѕСЂРёС‚РµС‚РѕРј."""
        if not self.user_promo_groups:
            return getattr(self, 'promo_group', None)

        try:
            # РЎРѕСЂС‚РёСЂСѓРµРј РїРѕ РїСЂРёРѕСЂРёС‚РµС‚Сѓ РіСЂСѓРїРїС‹ (СѓР±С‹РІР°РЅРёРµ), Р·Р°С‚РµРј РїРѕ ID РіСЂСѓРїРїС‹
            # РСЃРїРѕР»СЊР·СѓРµРј getattr РґР»СЏ Р·Р°С‰РёС‚С‹ РѕС‚ Р»РµРЅРёРІРѕР№ Р·Р°РіСЂСѓР·РєРё
            sorted_groups = sorted(
                self.user_promo_groups,
                key=lambda upg: (getattr(upg.promo_group, 'priority', 0) if upg.promo_group else 0, upg.promo_group_id),
                reverse=True,
            )

            if sorted_groups and sorted_groups[0].promo_group:
                return sorted_groups[0].promo_group
        except Exception:
            # Р•СЃР»Рё РІРѕР·РЅРёРєР»Р° РѕС€РёР±РєР° (РЅР°РїСЂРёРјРµСЂ, Р»РµРЅРёРІР°СЏ Р·Р°РіСЂСѓР·РєР°), fallback РЅР° СЃС‚Р°СЂСѓСЋ СЃРІСЏР·СЊ
            pass

        # Fallback РЅР° СЃС‚Р°СЂСѓСЋ СЃРІСЏР·СЊ РµСЃР»Рё РЅРѕРІР°СЏ РїСѓСЃС‚Р°СЏ РёР»Рё РІРѕР·РЅРёРєР»Р° РѕС€РёР±РєР°
        return getattr(self, 'promo_group', None)

    def get_promo_discount(self, category: str, period_days: int | None = None) -> int:
        primary_group = self.get_primary_promo_group()
        if not primary_group:
            return 0
        return primary_group.get_discount_percent(category, period_days)

    def add_balance(self, kopeks: int) -> None:
        self.balance_kopeks += kopeks

    def subtract_balance(self, kopeks: int) -> bool:
        if self.balance_kopeks >= kopeks:
            self.balance_kopeks -= kopeks
            return True
        return False


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)

    status = Column(String(20), default=SubscriptionStatus.TRIAL.value)
    is_trial = Column(Boolean, default=True)

    start_date = Column(AwareDateTime(), default=func.now())
    end_date = Column(AwareDateTime(), nullable=False)

    traffic_limit_gb = Column(Integer, default=0)
    traffic_used_gb = Column(Float, default=0.0)
    purchased_traffic_gb = Column(Integer, default=0)  # Р”РѕРєСѓРїР»РµРЅРЅС‹Р№ С‚СЂР°С„РёРє
    traffic_reset_at = Column(
        AwareDateTime(), nullable=True
    )  # Р”Р°С‚Р° СЃР±СЂРѕСЃР° РґРѕРєСѓРїР»РµРЅРЅРѕРіРѕ С‚СЂР°С„РёРєР° (30 РґРЅРµР№ РїРѕСЃР»Рµ РїРµСЂРІРѕР№ РґРѕРєСѓРїРєРё)

    subscription_url = Column(String, nullable=True)
    subscription_crypto_link = Column(String, nullable=True)

    device_limit = Column(Integer, default=1)
    modem_enabled = Column(Boolean, default=False)

    connected_squads = Column(JSON, default=list)

    autopay_enabled = Column(Boolean, default=False)
    autopay_days_before = Column(Integer, default=3)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    last_webhook_update_at = Column(AwareDateTime(), nullable=True)

    remnawave_short_uuid = Column(String(255), nullable=True)

    # РўР°СЂРёС„ (РґР»СЏ СЂРµР¶РёРјР° РїСЂРѕРґР°Р¶ "РўР°СЂРёС„С‹")
    tariff_id = Column(Integer, ForeignKey('tariffs.id', ondelete='SET NULL'), nullable=True, index=True)

    # РЎСѓС‚РѕС‡РЅР°СЏ РїРѕРґРїРёСЃРєР°
    is_daily_paused = Column(
        Boolean, default=False, nullable=False
    )  # РџСЂРёРѕСЃС‚Р°РЅРѕРІР»РµРЅР° Р»Рё СЃСѓС‚РѕС‡РЅР°СЏ РїРѕРґРїРёСЃРєР° РїРѕР»СЊР·РѕРІР°С‚РµР»РµРј
    last_daily_charge_at = Column(AwareDateTime(), nullable=True)  # Р’СЂРµРјСЏ РїРѕСЃР»РµРґРЅРµРіРѕ СЃСѓС‚РѕС‡РЅРѕРіРѕ СЃРїРёСЃР°РЅРёСЏ

    user = relationship('User', back_populates='subscription')
    tariff = relationship('Tariff', back_populates='subscriptions')
    family_group = relationship('FamilyGroup', back_populates='subscription', uselist=False)
    discount_offers = relationship('DiscountOffer', back_populates='subscription')
    temporary_accesses = relationship(
        'SubscriptionTemporaryAccess', back_populates='subscription', passive_deletes=True
    )
    traffic_purchases = relationship(
        'TrafficPurchase', back_populates='subscription', passive_deletes=True, cascade='all, delete-orphan'
    )

    @property
    def is_active(self) -> bool:
        current_time = datetime.now(UTC)
        end = _aware(self.end_date)
        return self.status == SubscriptionStatus.ACTIVE.value and end is not None and end > current_time

    @property
    def is_expired(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, РёСЃС‚С‘Рє Р»Рё СЃСЂРѕРє РїРѕРґРїРёСЃРєРё"""
        end = _aware(self.end_date)
        return end is not None and end <= datetime.now(UTC)

    @property
    def should_be_expired(self) -> bool:
        current_time = datetime.now(UTC)
        end = _aware(self.end_date)
        return self.status == SubscriptionStatus.ACTIVE.value and end is not None and end <= current_time

    @property
    def actual_status(self) -> str:
        current_time = datetime.now(UTC)
        end = _aware(self.end_date)

        if self.status == SubscriptionStatus.EXPIRED.value:
            return 'expired'

        if self.status == SubscriptionStatus.DISABLED.value:
            return 'disabled'

        if self.status == SubscriptionStatus.ACTIVE.value:
            if end is None or end <= current_time:
                return 'expired'
            return 'active'

        if self.status == SubscriptionStatus.TRIAL.value:
            if end is None or end <= current_time:
                return 'expired'
            return 'trial'

        return self.status

    @property
    def status_display(self) -> str:
        actual_status = self.actual_status

        if actual_status == 'expired':
            return 'рџ”ґ РСЃС‚РµРєР»Р°'
        if actual_status == 'active':
            if self.is_trial:
                return 'рџЋЇ РўРµСЃС‚РѕРІР°СЏ'
            return 'рџџў РђРєС‚РёРІРЅР°'
        if actual_status == 'disabled':
            return 'вљ« РћС‚РєР»СЋС‡РµРЅР°'
        if actual_status == 'trial':
            return 'рџЋЇ РўРµСЃС‚РѕРІР°СЏ'

        return 'вќ“ РќРµРёР·РІРµСЃС‚РЅРѕ'

    @property
    def status_emoji(self) -> str:
        actual_status = self.actual_status

        if actual_status == 'expired':
            return 'рџ”ґ'
        if actual_status == 'active':
            if self.is_trial:
                return 'рџЋЃ'
            return 'рџ’Ћ'
        if actual_status == 'disabled':
            return 'вљ«'
        if actual_status == 'trial':
            return 'рџЋЃ'

        return 'вќ“'

    @property
    def days_left(self) -> int:
        end = _aware(self.end_date)
        if end is None:
            return 0
        current_time = datetime.now(UTC)
        if end <= current_time:
            return 0
        delta = end - current_time
        return max(0, delta.days)

    @property
    def time_left_display(self) -> str:
        end = _aware(self.end_date)
        current_time = datetime.now(UTC)
        if end is None or end <= current_time:
            return 'РёСЃС‚С‘Рє'

        delta = end - current_time
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if days > 0:
            return f'{days} РґРЅ.'
        if hours > 0:
            return f'{hours} С‡.'
        return f'{minutes} РјРёРЅ.'

    @property
    def traffic_used_percent(self) -> float:
        if not self.traffic_limit_gb:
            return 0.0
        used = self.traffic_used_gb or 0.0
        return min((used / self.traffic_limit_gb) * 100, 100.0)

    def extend_subscription(self, days: int):
        end = _aware(self.end_date)
        if end and end > datetime.now(UTC):
            self.end_date = end + timedelta(days=days)
        else:
            self.end_date = datetime.now(UTC) + timedelta(days=days)

        if self.status == SubscriptionStatus.EXPIRED.value:
            self.status = SubscriptionStatus.ACTIVE.value

    def add_traffic(self, gb: int):
        if self.traffic_limit_gb == 0:
            return
        self.traffic_limit_gb += gb

    @property
    def is_daily_tariff(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, СЏРІР»СЏРµС‚СЃСЏ Р»Рё С‚Р°СЂРёС„ РїРѕРґРїРёСЃРєРё СЃСѓС‚РѕС‡РЅС‹Рј."""
        if self.tariff:
            return getattr(self.tariff, 'is_daily', False)
        return False

    @property
    def daily_price_kopeks(self) -> int:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃСѓС‚РѕС‡РЅСѓСЋ С†РµРЅСѓ С‚Р°СЂРёС„Р° РІ РєРѕРїРµР№РєР°С…."""
        if self.tariff:
            return getattr(self.tariff, 'daily_price_kopeks', 0)
        return 0

    @property
    def can_charge_daily(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, РјРѕР¶РЅРѕ Р»Рё СЃРїРёСЃР°С‚СЊ СЃСѓС‚РѕС‡РЅСѓСЋ РѕРїР»Р°С‚Сѓ."""
        if not self.is_daily_tariff:
            return False
        if self.is_daily_paused:
            return False
        if self.status != SubscriptionStatus.ACTIVE.value:
            return False
        return True

class FamilyGroup(Base):
    __tablename__ = 'family_groups'
    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False, unique=True)
    created_at = Column(AwareDateTime(), default=func.now(), nullable=False)
    owner = relationship('User', foreign_keys=[owner_user_id], back_populates='owned_family_group')
    subscription = relationship('Subscription', foreign_keys=[subscription_id], back_populates='family_group')
    members = relationship('FamilyMember', back_populates='family_group', cascade='all, delete-orphan')
    invites = relationship('FamilyInvite', back_populates='family_group', cascade='all, delete-orphan')
    devices = relationship('FamilyDevice', back_populates='family_group', cascade='all, delete-orphan')
class FamilyMember(Base):
    __tablename__ = 'family_members'
    __table_args__ = (
        UniqueConstraint('family_group_id', 'user_id', name='uq_family_members_group_user'),
        Index('ix_family_members_user_status', 'user_id', 'status'),
    )
    id = Column(Integer, primary_key=True, index=True)
    family_group_id = Column(Integer, ForeignKey('family_groups.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False, default='member')
    status = Column(String(20), nullable=False, default='invited')
    invited_by_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    invited_at = Column(AwareDateTime(), default=func.now(), nullable=False)
    accepted_at = Column(AwareDateTime(), nullable=True)
    removed_at = Column(AwareDateTime(), nullable=True)
    family_group = relationship('FamilyGroup', back_populates='members')
    user = relationship('User', foreign_keys=[user_id], back_populates='family_memberships')
    invited_by = relationship('User', foreign_keys=[invited_by_user_id])
class FamilyInvite(Base):
    __tablename__ = 'family_invites'
    __table_args__ = (
        UniqueConstraint('family_group_id', 'invitee_user_id', 'status', name='uq_family_invites_pending_tuple'),
        Index('ix_family_invites_invitee_status', 'invitee_user_id', 'status'),
    )
    id = Column(Integer, primary_key=True, index=True)
    family_group_id = Column(Integer, ForeignKey('family_groups.id', ondelete='CASCADE'), nullable=False)
    invitee_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    inviter_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(128), nullable=True, unique=True)
    status = Column(String(20), nullable=False, default='pending')
    created_at = Column(AwareDateTime(), default=func.now(), nullable=False)
    decided_at = Column(AwareDateTime(), nullable=True)
    expires_at = Column(AwareDateTime(), nullable=True)
    family_group = relationship('FamilyGroup', back_populates='invites')
    invitee = relationship('User', foreign_keys=[invitee_user_id], back_populates='received_family_invites')
    inviter = relationship('User', foreign_keys=[inviter_user_id], back_populates='sent_family_invites')
class FamilyDevice(Base):
    __tablename__ = 'family_devices'
    __table_args__ = (
        UniqueConstraint('family_group_id', 'hwid', name='uq_family_devices_group_hwid'),
        Index('ix_family_devices_owner', 'owner_user_id'),
    )
    id = Column(Integer, primary_key=True, index=True)
    family_group_id = Column(Integer, ForeignKey('family_groups.id', ondelete='CASCADE'), nullable=False)
    hwid = Column(String(255), nullable=False)
    owner_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subscription_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    platform = Column(String(100), nullable=True)
    device_model = Column(String(255), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now(), nullable=False)
    last_seen_at = Column(AwareDateTime(), default=func.now(), nullable=False)
    family_group = relationship('FamilyGroup', back_populates='devices')
    owner_user = relationship('User', foreign_keys=[owner_user_id])
    subscription_user = relationship('User', foreign_keys=[subscription_user_id])


class TrafficPurchase(Base):
    """Р”РѕРєСѓРїРєР° С‚СЂР°С„РёРєР° СЃ РёРЅРґРёРІРёРґСѓР°Р»СЊРЅРѕР№ РґР°С‚РѕР№ РёСЃС‚РµС‡РµРЅРёСЏ."""

    __tablename__ = 'traffic_purchases'

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False, index=True)

    traffic_gb = Column(Integer, nullable=False)  # РљРѕР»РёС‡РµСЃС‚РІРѕ Р“Р‘ РІ РїРѕРєСѓРїРєРµ
    expires_at = Column(AwareDateTime(), nullable=False, index=True)  # Р”Р°С‚Р° РёСЃС‚РµС‡РµРЅРёСЏ (РїРѕРєСѓРїРєР° + 30 РґРЅРµР№)

    created_at = Column(AwareDateTime(), default=func.now())

    subscription = relationship('Subscription', back_populates='traffic_purchases')

    @property
    def is_expired(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, РёСЃС‚РµРєР»Р° Р»Рё РґРѕРєСѓРїРєР°."""
        return datetime.now(UTC) >= _aware(self.expires_at)


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    type = Column(String(50), nullable=False)
    amount_kopeks = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)

    payment_method = Column(String(50), nullable=True)
    external_id = Column(String(255), nullable=True)

    is_completed = Column(Boolean, default=True)

    # NaloGO С‡РµРє
    receipt_uuid = Column(String(255), nullable=True, index=True)
    receipt_created_at = Column(AwareDateTime(), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    completed_at = Column(AwareDateTime(), nullable=True)

    user = relationship('User', back_populates='transactions')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100


class SubscriptionConversion(Base):
    __tablename__ = 'subscription_conversions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    converted_at = Column(AwareDateTime(), default=func.now())

    trial_duration_days = Column(Integer, nullable=True)

    payment_method = Column(String(50), nullable=True)

    first_payment_amount_kopeks = Column(Integer, nullable=True)

    first_paid_period_days = Column(Integer, nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())

    user = relationship('User', backref='subscription_conversions')

    @property
    def first_payment_amount_rubles(self) -> float:
        return (self.first_payment_amount_kopeks or 0) / 100

    def __repr__(self):
        return f'<SubscriptionConversion(user_id={self.user_id}, converted_at={self.converted_at})>'


class PromoCode(Base):
    __tablename__ = 'promocodes'

    id = Column(Integer, primary_key=True, index=True)

    code = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False)

    balance_bonus_kopeks = Column(Integer, default=0)
    subscription_days = Column(Integer, default=0)

    max_uses = Column(Integer, default=1)
    current_uses = Column(Integer, default=0)

    valid_from = Column(AwareDateTime(), default=func.now())
    valid_until = Column(AwareDateTime(), nullable=True)

    is_active = Column(Boolean, default=True)
    first_purchase_only = Column(Boolean, default=False)  # РўРѕР»СЊРєРѕ РґР»СЏ РїРµСЂРІРѕР№ РїРѕРєСѓРїРєРё

    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    promo_group_id = Column(Integer, ForeignKey('promo_groups.id', ondelete='SET NULL'), nullable=True, index=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    uses = relationship('PromoCodeUse', back_populates='promocode')
    promo_group = relationship('PromoGroup')

    @property
    def is_valid(self) -> bool:
        now = datetime.now(UTC)
        return (
            self.is_active
            and self.current_uses < self.max_uses
            and _aware(self.valid_from) <= now
            and (self.valid_until is None or _aware(self.valid_until) >= now)
        )

    @property
    def uses_left(self) -> int:
        return max(0, self.max_uses - self.current_uses)


class PromoCodeUse(Base):
    __tablename__ = 'promocode_uses'

    id = Column(Integer, primary_key=True, index=True)
    promocode_id = Column(Integer, ForeignKey('promocodes.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    used_at = Column(AwareDateTime(), default=func.now())

    promocode = relationship('PromoCode', back_populates='uses')
    user = relationship('User')


class ReferralEarning(Base):
    __tablename__ = 'referral_earnings'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    referral_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)

    amount_kopeks = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)

    referral_transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    campaign_id = Column(
        Integer, ForeignKey('advertising_campaigns.id', ondelete='SET NULL'), nullable=True, index=True
    )

    created_at = Column(AwareDateTime(), default=func.now())

    user = relationship('User', foreign_keys=[user_id], back_populates='referral_earnings')
    referral = relationship('User', foreign_keys=[referral_id])
    referral_transaction = relationship('Transaction')
    campaign = relationship('AdvertisingCampaign')

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100


class WithdrawalRequestStatus(Enum):
    """РЎС‚Р°С‚СѓСЃС‹ Р·Р°СЏРІРєРё РЅР° РІС‹РІРѕРґ СЂРµС„РµСЂР°Р»СЊРЅРѕРіРѕ Р±Р°Р»Р°РЅСЃР°."""

    PENDING = 'pending'  # РћР¶РёРґР°РµС‚ СЂР°СЃСЃРјРѕС‚СЂРµРЅРёСЏ
    APPROVED = 'approved'  # РћРґРѕР±СЂРµРЅР°
    REJECTED = 'rejected'  # РћС‚РєР»РѕРЅРµРЅР°
    COMPLETED = 'completed'  # Р’С‹РїРѕР»РЅРµРЅР° (РґРµРЅСЊРіРё РїРµСЂРµРІРµРґРµРЅС‹)
    CANCELLED = 'cancelled'  # РћС‚РјРµРЅРµРЅР° РїРѕР»СЊР·РѕРІР°С‚РµР»РµРј


class WithdrawalRequest(Base):
    """Р—Р°СЏРІРєР° РЅР° РІС‹РІРѕРґ СЂРµС„РµСЂР°Р»СЊРЅРѕРіРѕ Р±Р°Р»Р°РЅСЃР°."""

    __tablename__ = 'withdrawal_requests'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)

    amount_kopeks = Column(Integer, nullable=False)  # РЎСѓРјРјР° Рє РІС‹РІРѕРґСѓ
    status = Column(String(50), default=WithdrawalRequestStatus.PENDING.value, nullable=False, index=True)

    # Р”Р°РЅРЅС‹Рµ РґР»СЏ РІС‹РІРѕРґР° (Р·Р°РїРѕР»РЅСЏРµС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ)
    payment_details = Column(Text, nullable=True)  # Р РµРєРІРёР·РёС‚С‹ РґР»СЏ РїРµСЂРµРІРѕРґР°

    # РђРЅР°Р»РёР· РЅР° РѕС‚РјС‹РІР°РЅРёРµ
    risk_score = Column(Integer, default=0)  # 0-100, С‡РµРј РІС‹С€Рµ вЂ” С‚РµРј РїРѕРґРѕР·СЂРёС‚РµР»СЊРЅРµРµ
    risk_analysis = Column(Text, nullable=True)  # JSON СЃ РґРµС‚Р°Р»СЏРјРё Р°РЅР°Р»РёР·Р°

    # РћР±СЂР°Р±РѕС‚РєР° Р°РґРјРёРЅРѕРј
    processed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    processed_at = Column(AwareDateTime(), nullable=True)
    admin_comment = Column(Text, nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', foreign_keys=[user_id], backref='withdrawal_requests')
    admin = relationship('User', foreign_keys=[processed_by])

    @property
    def amount_rubles(self) -> float:
        return self.amount_kopeks / 100


class PartnerApplication(Base):
    """Р—Р°СЏРІРєР° РЅР° РїРѕР»СѓС‡РµРЅРёРµ СЃС‚Р°С‚СѓСЃР° РїР°СЂС‚РЅС‘СЂР°."""

    __tablename__ = 'partner_applications'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    company_name = Column(String(255), nullable=True)
    website_url = Column(String(500), nullable=True)
    telegram_channel = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    expected_monthly_referrals = Column(Integer, nullable=True)

    status = Column(String(20), default=PartnerStatus.PENDING.value, nullable=False)

    # РћР±СЂР°Р±РѕС‚РєР° Р°РґРјРёРЅРѕРј
    admin_comment = Column(Text, nullable=True)
    approved_commission_percent = Column(Integer, nullable=True)
    processed_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    processed_at = Column(AwareDateTime(), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', foreign_keys=[user_id], backref='partner_applications')
    admin = relationship('User', foreign_keys=[processed_by])


class ReferralContest(Base):
    __tablename__ = 'referral_contests'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prize_text = Column(Text, nullable=True)
    contest_type = Column(String(50), nullable=False, default='referral_paid')
    start_at = Column(AwareDateTime(), nullable=False)
    end_at = Column(AwareDateTime(), nullable=False)
    daily_summary_time = Column(Time, nullable=False, default=time(hour=12, minute=0))
    daily_summary_times = Column(String(255), nullable=True)  # CSV HH:MM
    timezone = Column(String(64), nullable=False, default='UTC')
    is_active = Column(Boolean, nullable=False, default=True)
    last_daily_summary_date = Column(Date, nullable=True)
    last_daily_summary_at = Column(AwareDateTime(), nullable=True)
    final_summary_sent = Column(Boolean, nullable=False, default=False)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    creator = relationship('User', backref='created_referral_contests')
    events = relationship(
        'ReferralContestEvent',
        back_populates='contest',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f"<ReferralContest id={self.id} title='{self.title}'>"


class ReferralContestEvent(Base):
    __tablename__ = 'referral_contest_events'
    __table_args__ = (
        UniqueConstraint(
            'contest_id',
            'referral_id',
            name='uq_referral_contest_referral',
        ),
        Index('idx_referral_contest_referrer', 'contest_id', 'referrer_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey('referral_contests.id', ondelete='CASCADE'), nullable=False)
    referrer_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    referral_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)
    amount_kopeks = Column(Integer, nullable=False, default=0)
    occurred_at = Column(AwareDateTime(), nullable=False, default=func.now())

    contest = relationship('ReferralContest', back_populates='events')
    referrer = relationship('User', foreign_keys=[referrer_id])
    referral = relationship('User', foreign_keys=[referral_id])

    def __repr__(self):
        return (
            f'<ReferralContestEvent contest={self.contest_id} referrer={self.referrer_id} referral={self.referral_id}>'
        )


class ReferralContestVirtualParticipant(Base):
    __tablename__ = 'referral_contest_virtual_participants'

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey('referral_contests.id', ondelete='CASCADE'), nullable=False)
    display_name = Column(String(255), nullable=False)
    referral_count = Column(Integer, nullable=False, default=0)
    total_amount_kopeks = Column(Integer, nullable=False, default=0)
    created_at = Column(AwareDateTime(), default=func.now())

    contest = relationship('ReferralContest')

    def __repr__(self):
        return (
            f"<ReferralContestVirtualParticipant id={self.id} name='{self.display_name}' count={self.referral_count}>"
        )


class ContestTemplate(Base):
    __tablename__ = 'contest_templates'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    prize_type = Column(String(20), nullable=False, default='days')
    prize_value = Column(String(50), nullable=False, default='1')
    max_winners = Column(Integer, nullable=False, default=1)
    attempts_per_user = Column(Integer, nullable=False, default=1)
    times_per_day = Column(Integer, nullable=False, default=1)
    schedule_times = Column(String(255), nullable=True)  # CSV of HH:MM in local TZ
    cooldown_hours = Column(Integer, nullable=False, default=24)
    payload = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    rounds = relationship('ContestRound', back_populates='template')


class ContestRound(Base):
    __tablename__ = 'contest_rounds'
    __table_args__ = (
        Index('idx_contest_round_status', 'status'),
        Index('idx_contest_round_template', 'template_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('contest_templates.id', ondelete='CASCADE'), nullable=False)
    starts_at = Column(AwareDateTime(), nullable=False)
    ends_at = Column(AwareDateTime(), nullable=False)
    status = Column(String(20), nullable=False, default='active')  # active, finished
    payload = Column(JSON, nullable=True)
    winners_count = Column(Integer, nullable=False, default=0)
    max_winners = Column(Integer, nullable=False, default=1)
    attempts_per_user = Column(Integer, nullable=False, default=1)
    message_id = Column(BigInteger, nullable=True)
    chat_id = Column(BigInteger, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    template = relationship('ContestTemplate', back_populates='rounds')
    attempts = relationship('ContestAttempt', back_populates='round', cascade='all, delete-orphan')


class ContestAttempt(Base):
    __tablename__ = 'contest_attempts'
    __table_args__ = (
        UniqueConstraint('round_id', 'user_id', name='uq_round_user_attempt'),
        Index('idx_contest_attempt_round', 'round_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey('contest_rounds.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    answer = Column(Text, nullable=True)
    is_winner = Column(Boolean, nullable=False, default=False)
    created_at = Column(AwareDateTime(), default=func.now())

    round = relationship('ContestRound', back_populates='attempts')
    user = relationship('User')


class Squad(Base):
    __tablename__ = 'squads'

    id = Column(Integer, primary_key=True, index=True)

    uuid = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    country_code = Column(String(5), nullable=True)

    is_available = Column(Boolean, default=True)
    price_kopeks = Column(Integer, default=0)

    description = Column(Text, nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    @property
    def price_rubles(self) -> float:
        return self.price_kopeks / 100


class ServiceRule(Base):
    __tablename__ = 'service_rules'

    id = Column(Integer, primary_key=True, index=True)

    order = Column(Integer, default=0)
    title = Column(String(255), nullable=False)

    content = Column(Text, nullable=False)

    is_active = Column(Boolean, default=True)

    language = Column(String(5), default='ru')

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())


class PrivacyPolicy(Base):
    __tablename__ = 'privacy_policies'

    id = Column(Integer, primary_key=True, index=True)
    language = Column(String(10), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())


class PublicOffer(Base):
    __tablename__ = 'public_offers'

    id = Column(Integer, primary_key=True, index=True)
    language = Column(String(10), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())


class FaqSetting(Base):
    __tablename__ = 'faq_settings'

    id = Column(Integer, primary_key=True, index=True)
    language = Column(String(10), nullable=False, unique=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())


class FaqPage(Base):
    __tablename__ = 'faq_pages'

    id = Column(Integer, primary_key=True, index=True)
    language = Column(String(10), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())


class SystemSetting(Base):
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())


class MonitoringLog(Base):
    __tablename__ = 'monitoring_logs'

    id = Column(Integer, primary_key=True, index=True)

    event_type = Column(String(100), nullable=False)

    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)

    is_success = Column(Boolean, default=True)

    created_at = Column(AwareDateTime(), default=func.now())

class UserNotification(Base):
    __tablename__ = 'user_notifications'
    __table_args__ = (Index('ix_user_notifications_user_read', 'user_id', 'read_at'),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True, default=dict)
    read_at = Column(AwareDateTime(), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now(), nullable=False)
    user = relationship('User', backref='user_notifications')
class SentNotification(Base):
    __tablename__ = 'sent_notifications'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False)
    notification_type = Column(String(50), nullable=False)
    days_before = Column(Integer, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())

    user = relationship('User', backref='sent_notifications')
    subscription = relationship('Subscription', backref=backref('sent_notifications', passive_deletes=True))


class SubscriptionEvent(Base):
    __tablename__ = 'subscription_events'

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True)
    amount_kopeks = Column(Integer, nullable=True)
    currency = Column(String(16), nullable=True)
    message = Column(Text, nullable=True)
    occurred_at = Column(AwareDateTime(), nullable=False, default=func.now())
    extra = Column(JSON, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())

    user = relationship('User', backref='subscription_events')
    subscription = relationship('Subscription', backref='subscription_events')
    transaction = relationship('Transaction', backref='subscription_events')


class DiscountOffer(Base):
    __tablename__ = 'discount_offers'
    __table_args__ = (Index('ix_discount_offers_user_type', 'user_id', 'notification_type'),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True)
    notification_type = Column(String(50), nullable=False)
    discount_percent = Column(Integer, nullable=False, default=0)
    bonus_amount_kopeks = Column(Integer, nullable=False, default=0)
    expires_at = Column(AwareDateTime(), nullable=False)
    claimed_at = Column(AwareDateTime(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    effect_type = Column(String(50), nullable=False, default='percent_discount')
    extra_data = Column(JSON, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    user = relationship('User', back_populates='discount_offers')
    subscription = relationship('Subscription', back_populates='discount_offers')
    logs = relationship('PromoOfferLog', back_populates='offer')


class PromoOfferTemplate(Base):
    __tablename__ = 'promo_offer_templates'
    __table_args__ = (Index('ix_promo_offer_templates_type', 'offer_type'),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    offer_type = Column(String(50), nullable=False)
    message_text = Column(Text, nullable=False)
    button_text = Column(String(255), nullable=False)
    valid_hours = Column(Integer, nullable=False, default=24)
    discount_percent = Column(Integer, nullable=False, default=0)
    bonus_amount_kopeks = Column(Integer, nullable=False, default=0)
    active_discount_hours = Column(Integer, nullable=True)
    test_duration_hours = Column(Integer, nullable=True)
    test_squad_uuids = Column(JSON, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    creator = relationship('User')


class SubscriptionTemporaryAccess(Base):
    __tablename__ = 'subscription_temporary_access'

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False)
    offer_id = Column(Integer, ForeignKey('discount_offers.id', ondelete='CASCADE'), nullable=False)
    squad_uuid = Column(String(255), nullable=False)
    expires_at = Column(AwareDateTime(), nullable=False)
    created_at = Column(AwareDateTime(), default=func.now())
    deactivated_at = Column(AwareDateTime(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    was_already_connected = Column(Boolean, default=False, nullable=False)

    subscription = relationship('Subscription', back_populates='temporary_accesses')
    offer = relationship('DiscountOffer')


class PromoOfferLog(Base):
    __tablename__ = 'promo_offer_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    offer_id = Column(Integer, ForeignKey('discount_offers.id', ondelete='SET NULL'), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    source = Column(String(100), nullable=True)
    percent = Column(Integer, nullable=True)
    effect_type = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())

    user = relationship('User', back_populates='promo_offer_logs')
    offer = relationship('DiscountOffer', back_populates='logs')


class BroadcastHistory(Base):
    __tablename__ = 'broadcast_history'

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(100), nullable=False)
    message_text = Column(Text, nullable=True)  # Nullable for email-only broadcasts
    has_media = Column(Boolean, default=False)
    media_type = Column(String(20), nullable=True)
    media_file_id = Column(String(255), nullable=True)
    media_caption = Column(Text, nullable=True)
    total_count = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    blocked_count = Column(Integer, default=0)
    status = Column(String(50), default='in_progress')
    admin_id = Column(Integer, ForeignKey('users.id'))
    admin_name = Column(String(255))
    created_at = Column(AwareDateTime(), server_default=func.now())
    completed_at = Column(AwareDateTime(), nullable=True)

    # Email broadcast fields
    channel = Column(String(20), default='telegram', nullable=False)  # telegram|email|both
    email_subject = Column(String(255), nullable=True)
    email_html_content = Column(Text, nullable=True)

    admin = relationship('User', back_populates='broadcasts')


class Poll(Base):
    __tablename__ = 'polls'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    reward_enabled = Column(Boolean, nullable=False, default=False)
    reward_amount_kopeks = Column(Integer, nullable=False, default=0)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now(), nullable=False)
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now(), nullable=False)

    creator = relationship('User', backref='created_polls', foreign_keys=[created_by])
    questions = relationship(
        'PollQuestion',
        back_populates='poll',
        cascade='all, delete-orphan',
        order_by='PollQuestion.order',
    )
    responses = relationship(
        'PollResponse',
        back_populates='poll',
        cascade='all, delete-orphan',
    )


class PollQuestion(Base):
    __tablename__ = 'poll_questions'

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey('polls.id', ondelete='CASCADE'), nullable=False, index=True)
    text = Column(Text, nullable=False)
    order = Column(Integer, nullable=False, default=0)

    poll = relationship('Poll', back_populates='questions')
    options = relationship(
        'PollOption',
        back_populates='question',
        cascade='all, delete-orphan',
        order_by='PollOption.order',
    )
    answers = relationship('PollAnswer', back_populates='question')


class PollOption(Base):
    __tablename__ = 'poll_options'

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey('poll_questions.id', ondelete='CASCADE'), nullable=False, index=True)
    text = Column(Text, nullable=False)
    order = Column(Integer, nullable=False, default=0)

    question = relationship('PollQuestion', back_populates='options')
    answers = relationship('PollAnswer', back_populates='option')


class PollResponse(Base):
    __tablename__ = 'poll_responses'

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey('polls.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    sent_at = Column(AwareDateTime(), default=func.now(), nullable=False)
    started_at = Column(AwareDateTime(), nullable=True)
    completed_at = Column(AwareDateTime(), nullable=True)
    reward_given = Column(Boolean, nullable=False, default=False)
    reward_amount_kopeks = Column(Integer, nullable=False, default=0)

    poll = relationship('Poll', back_populates='responses')
    user = relationship('User', back_populates='poll_responses')
    answers = relationship(
        'PollAnswer',
        back_populates='response',
        cascade='all, delete-orphan',
    )

    __table_args__ = (UniqueConstraint('poll_id', 'user_id', name='uq_poll_user'),)


class PollAnswer(Base):
    __tablename__ = 'poll_answers'

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey('poll_responses.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey('poll_questions.id', ondelete='CASCADE'), nullable=False, index=True)
    option_id = Column(Integer, ForeignKey('poll_options.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(AwareDateTime(), default=func.now(), nullable=False)

    response = relationship('PollResponse', back_populates='answers')
    question = relationship('PollQuestion', back_populates='answers')
    option = relationship('PollOption', back_populates='answers')

    __table_args__ = (UniqueConstraint('response_id', 'question_id', name='uq_poll_answer_unique'),)


class ServerSquad(Base):
    __tablename__ = 'server_squads'

    id = Column(Integer, primary_key=True, index=True)

    squad_uuid = Column(String(255), unique=True, nullable=False, index=True)

    display_name = Column(String(255), nullable=False)

    original_name = Column(String(255), nullable=True)

    country_code = Column(String(5), nullable=True)

    is_available = Column(Boolean, default=True)
    is_trial_eligible = Column(Boolean, default=False, nullable=False)

    price_kopeks = Column(Integer, default=0)

    description = Column(Text, nullable=True)

    sort_order = Column(Integer, default=0)

    max_users = Column(Integer, nullable=True)
    current_users = Column(Integer, default=0)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    allowed_promo_groups = relationship(
        'PromoGroup',
        secondary=server_squad_promo_groups,
        back_populates='server_squads',
        lazy='selectin',
    )

    @property
    def price_rubles(self) -> float:
        return self.price_kopeks / 100

    @property
    def is_full(self) -> bool:
        if self.max_users is None:
            return False
        return self.current_users >= self.max_users

    @property
    def availability_status(self) -> str:
        if not self.is_available:
            return 'РќРµРґРѕСЃС‚СѓРїРµРЅ'
        if self.is_full:
            return 'РџРµСЂРµРїРѕР»РЅРµРЅ'
        return 'Р”РѕСЃС‚СѓРїРµРЅ'


class SubscriptionServer(Base):
    __tablename__ = 'subscription_servers'

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    server_squad_id = Column(Integer, ForeignKey('server_squads.id'), nullable=False)

    connected_at = Column(AwareDateTime(), default=func.now())

    paid_price_kopeks = Column(Integer, default=0)

    subscription = relationship('Subscription', backref=backref('subscription_servers', passive_deletes=True))
    server_squad = relationship('ServerSquad', backref='subscription_servers')


class SupportAuditLog(Base):
    __tablename__ = 'support_audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    actor_telegram_id = Column(BigInteger, nullable=True)  # Can be None for email-only users
    is_moderator = Column(Boolean, default=False)
    action = Column(String(50), nullable=False)  # close_ticket, block_user_timed, block_user_perm, unblock_user
    ticket_id = Column(Integer, ForeignKey('tickets.id', ondelete='SET NULL'), nullable=True)
    target_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())

    actor = relationship('User', foreign_keys=[actor_user_id])
    ticket = relationship('Ticket', foreign_keys=[ticket_id])


class UserMessage(Base):
    __tablename__ = 'user_messages'
    id = Column(Integer, primary_key=True, index=True)
    message_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())
    creator = relationship('User', backref='created_messages')

    def __repr__(self):
        return f"<UserMessage(id={self.id}, active={self.is_active}, text='{self.message_text[:50]}...')>"


class WelcomeText(Base):
    __tablename__ = 'welcome_texts'

    id = Column(Integer, primary_key=True, index=True)
    text_content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    is_enabled = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    creator = relationship('User', backref='created_welcome_texts')


class PinnedMessage(Base):
    __tablename__ = 'pinned_messages'

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False, default='')
    media_type = Column(String(32), nullable=True)
    media_file_id = Column(String(255), nullable=True)
    send_before_menu = Column(Boolean, nullable=False, server_default='1', default=True)
    send_on_every_start = Column(Boolean, nullable=False, server_default='1', default=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    creator = relationship('User', backref='pinned_messages')


class AdvertisingCampaign(Base):
    __tablename__ = 'advertising_campaigns'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    start_parameter = Column(String(64), nullable=False, unique=True, index=True)
    bonus_type = Column(String(20), nullable=False)

    balance_bonus_kopeks = Column(Integer, default=0)

    subscription_duration_days = Column(Integer, nullable=True)
    subscription_traffic_gb = Column(Integer, nullable=True)
    subscription_device_limit = Column(Integer, nullable=True)
    subscription_squads = Column(JSON, default=list)

    # РџРѕР»СЏ РґР»СЏ С‚РёРїР° "tariff" - РІС‹РґР°С‡Р° С‚Р°СЂРёС„Р°
    tariff_id = Column(Integer, ForeignKey('tariffs.id', ondelete='SET NULL'), nullable=True)
    tariff_duration_days = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True)

    # РџСЂРёРІСЏР·РєР° Рє РїР°СЂС‚РЅС‘СЂСѓ
    partner_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    registrations = relationship('AdvertisingCampaignRegistration', back_populates='campaign')
    tariff = relationship('Tariff', foreign_keys=[tariff_id])
    partner = relationship('User', foreign_keys=[partner_user_id])

    @property
    def is_balance_bonus(self) -> bool:
        return self.bonus_type == 'balance'

    @property
    def is_subscription_bonus(self) -> bool:
        return self.bonus_type == 'subscription'

    @property
    def is_none_bonus(self) -> bool:
        """РЎСЃС‹Р»РєР° Р±РµР· РЅР°РіСЂР°РґС‹ - С‚РѕР»СЊРєРѕ РґР»СЏ РѕС‚СЃР»РµР¶РёРІР°РЅРёСЏ."""
        return self.bonus_type == 'none'

    @property
    def is_tariff_bonus(self) -> bool:
        """Р’С‹РґР°С‡Р° С‚Р°СЂРёС„Р° РЅР° РѕРїСЂРµРґРµР»С‘РЅРЅРѕРµ РІСЂРµРјСЏ."""
        return self.bonus_type == 'tariff'


class AdvertisingCampaignRegistration(Base):
    __tablename__ = 'advertising_campaign_registrations'
    __table_args__ = (UniqueConstraint('campaign_id', 'user_id', name='uq_campaign_user'),)

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey('advertising_campaigns.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    bonus_type = Column(String(20), nullable=False)
    balance_bonus_kopeks = Column(Integer, default=0)
    subscription_duration_days = Column(Integer, nullable=True)

    # РџРѕР»СЏ РґР»СЏ С‚РёРїР° "tariff"
    tariff_id = Column(Integer, ForeignKey('tariffs.id', ondelete='SET NULL'), nullable=True)
    tariff_duration_days = Column(Integer, nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())

    campaign = relationship('AdvertisingCampaign', back_populates='registrations')
    user = relationship('User')
    tariff = relationship('Tariff')

    @property
    def balance_bonus_rubles(self) -> float:
        return (self.balance_bonus_kopeks or 0) / 100


class TicketStatus(Enum):
    OPEN = 'open'
    ANSWERED = 'answered'
    CLOSED = 'closed'
    PENDING = 'pending'


class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    title = Column(String(255), nullable=False)
    status = Column(String(20), default=TicketStatus.OPEN.value, nullable=False)
    priority = Column(String(20), default='normal', nullable=False)  # low, normal, high, urgent
    # Р‘Р»РѕРєРёСЂРѕРІРєР° РѕС‚РІРµС‚РѕРІ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РІ СЌС‚РѕРј С‚РёРєРµС‚Рµ
    user_reply_block_permanent = Column(Boolean, default=False, nullable=False)
    user_reply_block_until = Column(AwareDateTime(), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())
    closed_at = Column(AwareDateTime(), nullable=True)
    # SLA reminders
    last_sla_reminder_at = Column(AwareDateTime(), nullable=True)

    # РЎРІСЏР·Рё
    user = relationship('User', backref='tickets')
    messages = relationship('TicketMessage', back_populates='ticket', cascade='all, delete-orphan')

    @property
    def is_open(self) -> bool:
        return self.status == TicketStatus.OPEN.value

    @property
    def is_answered(self) -> bool:
        return self.status == TicketStatus.ANSWERED.value

    @property
    def is_closed(self) -> bool:
        return self.status == TicketStatus.CLOSED.value

    @property
    def is_pending(self) -> bool:
        return self.status == TicketStatus.PENDING.value

    @property
    def is_user_reply_blocked(self) -> bool:
        if self.user_reply_block_permanent:
            return True
        if self.user_reply_block_until:
            return _aware(self.user_reply_block_until) > datetime.now(UTC)
        return False

    @property
    def status_emoji(self) -> str:
        status_emojis = {
            TicketStatus.OPEN.value: 'рџ”ґ',
            TicketStatus.ANSWERED.value: 'рџџЎ',
            TicketStatus.CLOSED.value: 'рџџў',
            TicketStatus.PENDING.value: 'вЏі',
        }
        return status_emojis.get(self.status, 'вќ“')

    @property
    def priority_emoji(self) -> str:
        priority_emojis = {'low': 'рџџў', 'normal': 'рџџЎ', 'high': 'рџџ ', 'urgent': 'рџ”ґ'}
        return priority_emojis.get(self.priority, 'рџџЎ')

    def __repr__(self):
        return f"<Ticket(id={self.id}, user_id={self.user_id}, status={self.status}, title='{self.title[:30]}...')>"


class TicketMessage(Base):
    __tablename__ = 'ticket_messages'

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    message_text = Column(Text, nullable=False)
    is_from_admin = Column(Boolean, default=False, nullable=False)

    # Р”Р»СЏ РјРµРґРёР° С„Р°Р№Р»РѕРІ
    has_media = Column(Boolean, default=False)
    media_type = Column(String(20), nullable=True)  # photo, video, document, voice, etc.
    media_file_id = Column(String(255), nullable=True)
    media_caption = Column(Text, nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())

    # РЎРІСЏР·Рё
    ticket = relationship('Ticket', back_populates='messages')
    user = relationship('User')

    @property
    def is_user_message(self) -> bool:
        return not self.is_from_admin

    @property
    def is_admin_message(self) -> bool:
        return self.is_from_admin

    def __repr__(self):
        return f"<TicketMessage(id={self.id}, ticket_id={self.ticket_id}, is_admin={self.is_from_admin}, text='{self.message_text[:30]}...')>"


class WebApiToken(Base):
    __tablename__ = 'web_api_tokens'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    token_prefix = Column(String(32), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())
    expires_at = Column(AwareDateTime(), nullable=True)
    last_used_at = Column(AwareDateTime(), nullable=True)
    last_used_ip = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        status = 'active' if self.is_active else 'revoked'
        return f"<WebApiToken id={self.id} name='{self.name}' status={status}>"


class MainMenuButton(Base):
    __tablename__ = 'main_menu_buttons'

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(64), nullable=False)
    action_type = Column(String(20), nullable=False)
    action_value = Column(Text, nullable=False)
    visibility = Column(String(20), nullable=False, default=MainMenuButtonVisibility.ALL.value)
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    __table_args__ = (Index('ix_main_menu_buttons_order', 'display_order', 'id'),)

    @property
    def action_type_enum(self) -> MainMenuButtonActionType:
        try:
            return MainMenuButtonActionType(self.action_type)
        except ValueError:
            return MainMenuButtonActionType.URL

    @property
    def visibility_enum(self) -> MainMenuButtonVisibility:
        try:
            return MainMenuButtonVisibility(self.visibility)
        except ValueError:
            return MainMenuButtonVisibility.ALL

    def __repr__(self) -> str:
        return (
            f"<MainMenuButton id={self.id} text='{self.text}' "
            f'action={self.action_type} visibility={self.visibility} active={self.is_active}>'
        )


class MenuLayoutHistory(Base):
    """РСЃС‚РѕСЂРёСЏ РёР·РјРµРЅРµРЅРёР№ РєРѕРЅС„РёРіСѓСЂР°С†РёРё РјРµРЅСЋ."""

    __tablename__ = 'menu_layout_history'

    id = Column(Integer, primary_key=True, index=True)
    config_json = Column(Text, nullable=False)  # РџРѕР»РЅР°СЏ РєРѕРЅС„РёРіСѓСЂР°С†РёСЏ РІ JSON
    action = Column(String(50), nullable=False)  # update, reset, import
    changes_summary = Column(Text, nullable=True)  # РљСЂР°С‚РєРѕРµ РѕРїРёСЃР°РЅРёРµ РёР·РјРµРЅРµРЅРёР№
    user_info = Column(String(255), nullable=True)  # РРЅС„РѕСЂРјР°С†РёСЏ Рѕ РїРѕР»СЊР·РѕРІР°С‚РµР»Рµ/С‚РѕРєРµРЅРµ
    created_at = Column(AwareDateTime(), default=func.now(), index=True)

    __table_args__ = (Index('ix_menu_layout_history_created', 'created_at'),)

    def __repr__(self) -> str:
        return f"<MenuLayoutHistory id={self.id} action='{self.action}' created_at={self.created_at}>"


class ButtonClickLog(Base):
    """Р›РѕРіРё РєР»РёРєРѕРІ РїРѕ РєРЅРѕРїРєР°Рј РјРµРЅСЋ."""

    __tablename__ = 'button_click_logs'

    id = Column(Integer, primary_key=True, index=True)
    button_id = Column(String(100), nullable=False, index=True)  # ID РєРЅРѕРїРєРё
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    callback_data = Column(String(255), nullable=True)  # callback_data РєРЅРѕРїРєРё
    clicked_at = Column(AwareDateTime(), default=func.now(), index=True)

    # Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅР°СЏ РёРЅС„РѕСЂРјР°С†РёСЏ
    button_type = Column(String(20), nullable=True, index=True)  # builtin, callback, url, mini_app
    button_text = Column(String(255), nullable=True)  # РўРµРєСЃС‚ РєРЅРѕРїРєРё РЅР° РјРѕРјРµРЅС‚ РєР»РёРєР°

    __table_args__ = (
        Index('ix_button_click_logs_button_date', 'button_id', 'clicked_at'),
        Index('ix_button_click_logs_user_date', 'user_id', 'clicked_at'),
    )

    # РЎРІСЏР·Рё
    user = relationship('User', foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<ButtonClickLog id={self.id} button='{self.button_id}' user={self.user_id} at={self.clicked_at}>"


class Webhook(Base):
    """Webhook РєРѕРЅС„РёРіСѓСЂР°С†РёСЏ РґР»СЏ РїРѕРґРїРёСЃРєРё РЅР° СЃРѕР±С‹С‚РёСЏ."""

    __tablename__ = 'webhooks'
    __table_args__ = (
        Index('ix_webhooks_event_type', 'event_type'),
        Index('ix_webhooks_is_active', 'is_active'),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    secret = Column(String(128), nullable=True)  # РЎРµРєСЂРµС‚ РґР»СЏ РїРѕРґРїРёСЃРё payload
    event_type = Column(String(50), nullable=False)  # user.created, payment.completed, ticket.created, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())
    last_triggered_at = Column(AwareDateTime(), nullable=True)
    failure_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)

    deliveries = relationship('WebhookDelivery', back_populates='webhook', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        status = 'active' if self.is_active else 'inactive'
        return f"<Webhook id={self.id} name='{self.name}' event='{self.event_type}' status={status}>"


class WebhookDelivery(Base):
    """РСЃС‚РѕСЂРёСЏ РґРѕСЃС‚Р°РІРєРё webhooks."""

    __tablename__ = 'webhook_deliveries'
    __table_args__ = (
        Index('ix_webhook_deliveries_webhook_created', 'webhook_id', 'created_at'),
        Index('ix_webhook_deliveries_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey('webhooks.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)  # РћС‚РїСЂР°РІР»РµРЅРЅС‹Р№ payload
    response_status = Column(Integer, nullable=True)  # HTTP СЃС‚Р°С‚СѓСЃ РѕС‚РІРµС‚Р°
    response_body = Column(Text, nullable=True)  # РўРµР»Рѕ РѕС‚РІРµС‚Р° (РјРѕР¶РµС‚ Р±С‹С‚СЊ РѕР±СЂРµР·Р°РЅРѕ)
    status = Column(String(20), nullable=False)  # pending, success, failed
    error_message = Column(Text, nullable=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    created_at = Column(AwareDateTime(), default=func.now())
    delivered_at = Column(AwareDateTime(), nullable=True)
    next_retry_at = Column(AwareDateTime(), nullable=True)

    webhook = relationship('Webhook', back_populates='deliveries')

    def __repr__(self) -> str:
        return f"<WebhookDelivery id={self.id} webhook_id={self.webhook_id} status='{self.status}' event='{self.event_type}'>"


class CabinetRefreshToken(Base):
    """Refresh tokens for cabinet JWT authentication."""

    __tablename__ = 'cabinet_refresh_tokens'
    __table_args__ = (Index('ix_cabinet_refresh_tokens_user', 'user_id'),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    device_info = Column(String(500), nullable=True)
    expires_at = Column(AwareDateTime(), nullable=False)
    created_at = Column(AwareDateTime(), default=func.now())
    revoked_at = Column(AwareDateTime(), nullable=True)

    user = relationship('User', backref='cabinet_tokens')

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > _aware(self.expires_at)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_revoked

    def __repr__(self) -> str:
        status = 'valid' if self.is_valid else ('revoked' if self.is_revoked else 'expired')
        return f'<CabinetRefreshToken id={self.id} user_id={self.user_id} status={status}>'


# ==================== FORTUNE WHEEL ====================


class WheelConfig(Base):
    """Р“Р»РѕР±Р°Р»СЊРЅР°СЏ РєРѕРЅС„РёРіСѓСЂР°С†РёСЏ РєРѕР»РµСЃР° СѓРґР°С‡Рё."""

    __tablename__ = 'wheel_configs'

    id = Column(Integer, primary_key=True, index=True)

    # РћСЃРЅРѕРІРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё
    is_enabled = Column(Boolean, default=False, nullable=False)
    name = Column(String(255), default='РљРѕР»РµСЃРѕ СѓРґР°С‡Рё', nullable=False)

    # РЎС‚РѕРёРјРѕСЃС‚СЊ СЃРїРёРЅР°
    spin_cost_stars = Column(Integer, default=10, nullable=False)  # РЎС‚РѕРёРјРѕСЃС‚СЊ РІ Stars
    spin_cost_days = Column(Integer, default=1, nullable=False)  # РЎС‚РѕРёРјРѕСЃС‚СЊ РІ РґРЅСЏС… РїРѕРґРїРёСЃРєРё
    spin_cost_stars_enabled = Column(Boolean, default=True, nullable=False)
    spin_cost_days_enabled = Column(Boolean, default=True, nullable=False)

    # RTP РЅР°СЃС‚СЂРѕР№РєРё (Return to Player) - РїСЂРѕС†РµРЅС‚ РІРѕР·РІСЂР°С‚Р° 0-100
    rtp_percent = Column(Integer, default=80, nullable=False)

    # Р›РёРјРёС‚С‹
    daily_spin_limit = Column(Integer, default=5, nullable=False)  # 0 = Р±РµР· Р»РёРјРёС‚Р°
    min_subscription_days_for_day_payment = Column(Integer, default=3, nullable=False)

    # Р“РµРЅРµСЂР°С†РёСЏ РїСЂРѕРјРѕРєРѕРґРѕРІ
    promo_prefix = Column(String(20), default='WHEEL', nullable=False)
    promo_validity_days = Column(Integer, default=7, nullable=False)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    prizes = relationship('WheelPrize', back_populates='config', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<WheelConfig id={self.id} enabled={self.is_enabled} rtp={self.rtp_percent}%>'


class WheelPrize(Base):
    """РџСЂРёР· РЅР° РєРѕР»РµСЃРµ СѓРґР°С‡Рё."""

    __tablename__ = 'wheel_prizes'

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey('wheel_configs.id', ondelete='CASCADE'), nullable=False)

    # РўРёРї Рё Р·РЅР°С‡РµРЅРёРµ РїСЂРёР·Р°
    prize_type = Column(String(50), nullable=False)  # WheelPrizeType
    prize_value = Column(Integer, default=0, nullable=False)  # Р”РЅРё/РєРѕРїРµР№РєРё/GB РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ С‚РёРїР°

    # РћС‚РѕР±СЂР°Р¶РµРЅРёРµ
    display_name = Column(String(100), nullable=False)
    emoji = Column(String(10), default='рџЋЃ', nullable=False)
    color = Column(String(20), default='#3B82F6', nullable=False)  # HEX С†РІРµС‚ СЃРµРєС‚РѕСЂР°

    # РЎС‚РѕРёРјРѕСЃС‚СЊ РїСЂРёР·Р° РґР»СЏ СЂР°СЃС‡РµС‚Р° RTP (РІ РєРѕРїРµР№РєР°С…)
    prize_value_kopeks = Column(Integer, default=0, nullable=False)

    # РџРѕСЂСЏРґРѕРє Рё РІРµСЂРѕСЏС‚РЅРѕСЃС‚СЊ
    sort_order = Column(Integer, default=0, nullable=False)
    manual_probability = Column(Float, nullable=True)  # Р•СЃР»Рё Р·Р°РґР°РЅРѕ - РёРіРЅРѕСЂРёСЂСѓРµС‚ RTP СЂР°СЃС‡РµС‚ (0.0-1.0)
    is_active = Column(Boolean, default=True, nullable=False)

    # РќР°СЃС‚СЂРѕР№РєРё РіРµРЅРµСЂРёСЂСѓРµРјРѕРіРѕ РїСЂРѕРјРѕРєРѕРґР° (С‚РѕР»СЊРєРѕ РґР»СЏ prize_type=promocode)
    promo_balance_bonus_kopeks = Column(Integer, default=0)
    promo_subscription_days = Column(Integer, default=0)
    promo_traffic_gb = Column(Integer, default=0)

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    config = relationship('WheelConfig', back_populates='prizes')
    spins = relationship('WheelSpin', back_populates='prize')

    def __repr__(self) -> str:
        return f"<WheelPrize id={self.id} type={self.prize_type} name='{self.display_name}'>"


class WheelSpin(Base):
    """РСЃС‚РѕСЂРёСЏ СЃРїРёРЅРѕРІ РєРѕР»РµСЃР° СѓРґР°С‡Рё."""

    __tablename__ = 'wheel_spins'
    __table_args__ = (Index('ix_wheel_spins_user_created', 'user_id', 'created_at'),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    prize_id = Column(Integer, ForeignKey('wheel_prizes.id', ondelete='SET NULL'), nullable=True)

    # РЎРїРѕСЃРѕР± РѕРїР»Р°С‚С‹
    payment_type = Column(String(50), nullable=False)  # WheelSpinPaymentType
    payment_amount = Column(Integer, nullable=False)  # Stars РёР»Рё РґРЅРё
    payment_value_kopeks = Column(Integer, nullable=False)  # Р­РєРІРёРІР°Р»РµРЅС‚ РІ РєРѕРїРµР№РєР°С… РґР»СЏ СЃС‚Р°С‚РёСЃС‚РёРєРё

    # Р РµР·СѓР»СЊС‚Р°С‚
    prize_type = Column(String(50), nullable=False)  # РљРѕРїРёСЂСѓРµРј РёР· WheelPrize РЅР° РјРѕРјРµРЅС‚ СЃРїРёРЅР°
    prize_value = Column(Integer, nullable=False)
    prize_display_name = Column(String(100), nullable=False)
    prize_value_kopeks = Column(Integer, nullable=False)  # РЎС‚РѕРёРјРѕСЃС‚СЊ РїСЂРёР·Р° РІ РєРѕРїРµР№РєР°С…

    # РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ РїСЂРѕРјРѕРєРѕРґ (РµСЃР»Рё РїСЂРёР· - РїСЂРѕРјРѕРєРѕРґ)
    generated_promocode_id = Column(Integer, ForeignKey('promocodes.id'), nullable=True)

    # Р¤Р»Р°Рі СѓСЃРїРµС€РЅРѕРіРѕ РЅР°С‡РёСЃР»РµРЅРёСЏ
    is_applied = Column(Boolean, default=False, nullable=False)
    applied_at = Column(AwareDateTime(), nullable=True)

    created_at = Column(AwareDateTime(), default=func.now())

    user = relationship('User', backref='wheel_spins')
    prize = relationship('WheelPrize', back_populates='spins')
    generated_promocode = relationship('PromoCode')

    @property
    def prize_value_rubles(self) -> float:
        """РЎС‚РѕРёРјРѕСЃС‚СЊ РїСЂРёР·Р° РІ СЂСѓР±Р»СЏС…."""
        return self.prize_value_kopeks / 100

    @property
    def payment_value_rubles(self) -> float:
        """РЎС‚РѕРёРјРѕСЃС‚СЊ РѕРїР»Р°С‚С‹ РІ СЂСѓР±Р»СЏС…."""
        return self.payment_value_kopeks / 100

    def __repr__(self) -> str:
        return f"<WheelSpin id={self.id} user_id={self.user_id} prize='{self.prize_display_name}'>"


class TicketNotification(Base):
    """РЈРІРµРґРѕРјР»РµРЅРёСЏ Рѕ С‚РёРєРµС‚Р°С… РґР»СЏ РєР°Р±РёРЅРµС‚Р° (РІРµР±-РёРЅС‚РµСЂС„РµР№СЃ)."""

    __tablename__ = 'ticket_notifications'
    __table_args__ = (
        Index('ix_ticket_notifications_user_read', 'user_id', 'is_read'),
        Index('ix_ticket_notifications_admin_read', 'is_for_admin', 'is_read'),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # РўРёРї СѓРІРµРґРѕРјР»РµРЅРёСЏ: new_ticket, admin_reply, user_reply
    notification_type = Column(String(50), nullable=False)

    # РўРµРєСЃС‚ СѓРІРµРґРѕРјР»РµРЅРёСЏ
    message = Column(Text, nullable=True)

    # Р”Р»СЏ Р°РґРјРёРЅР° РёР»Рё РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    is_for_admin = Column(Boolean, default=False, nullable=False)

    # РџСЂРѕС‡РёС‚Р°РЅРѕ Р»Рё СѓРІРµРґРѕРјР»РµРЅРёРµ
    is_read = Column(Boolean, default=False, nullable=False)

    created_at = Column(AwareDateTime(), default=func.now())
    read_at = Column(AwareDateTime(), nullable=True)

    ticket = relationship('Ticket', backref='notifications')
    user = relationship('User', backref='ticket_notifications')

    def __repr__(self) -> str:
        return f'<TicketNotification id={self.id} type={self.notification_type} for_admin={self.is_for_admin}>'


# ==================== PAYMENT METHOD CONFIG ====================


class PaymentMethodConfig(Base):
    """РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ РїР»Р°С‚С‘Р¶РЅС‹С… РјРµС‚РѕРґРѕРІ РІ РєР°Р±РёРЅРµС‚Рµ."""

    __tablename__ = 'payment_method_configs'

    id = Column(Integer, primary_key=True, index=True)

    # РЈРЅРёРєР°Р»СЊРЅС‹Р№ РёРґРµРЅС‚РёС„РёРєР°С‚РѕСЂ РјРµС‚РѕРґР° (СЃРѕРІРїР°РґР°РµС‚ СЃ PaymentMethod enum: 'yookassa', 'cryptobot' Рё С‚.Рґ.)
    method_id = Column(String(50), unique=True, nullable=False, index=True)

    # РџРѕСЂСЏРґРѕРє РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ (РјРµРЅСЊС€Рµ = РІС‹С€Рµ)
    sort_order = Column(Integer, nullable=False, default=0, index=True)

    # Р’РєР»СЋС‡С‘РЅ/РІС‹РєР»СЋС‡РµРЅ (РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕ Рє env-РїРµСЂРµРјРµРЅРЅС‹Рј)
    is_enabled = Column(Boolean, nullable=False, default=True)

    # РџРµСЂРµРѕРїСЂРµРґРµР»РµРЅРёРµ РѕС‚РѕР±СЂР°Р¶Р°РµРјРѕРіРѕ РёРјРµРЅРё (null = РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ РёР· env)
    display_name = Column(String(255), nullable=True)

    # РџРѕРґ-РѕРїС†РёРё РІРєР»СЋС‡РµРЅРёСЏ/РІС‹РєР»СЋС‡РµРЅРёСЏ (JSON): {"card": true, "sbp": false}
    # Р”Р»СЏ РјРµС‚РѕРґРѕРІ СЃ РІР°СЂРёР°РЅС‚Р°РјРё: yookassa, pal24, platega
    sub_options = Column(JSON, nullable=True, default=None)

    # РџРµСЂРµРѕРїСЂРµРґРµР»РµРЅРёРµ РјРёРЅ/РјР°РєСЃ СЃСѓРјРј (null = РёР· env)
    min_amount_kopeks = Column(Integer, nullable=True)
    max_amount_kopeks = Column(Integer, nullable=True)

    # --- РЈСЃР»РѕРІРёСЏ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ ---

    # Р¤РёР»СЊС‚СЂ РїРѕ С‚РёРїСѓ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ: 'all', 'telegram', 'email'
    user_type_filter = Column(String(20), nullable=False, default='all')

    # Р¤РёР»СЊС‚СЂ РїРѕ РїРµСЂРІРѕРјСѓ РїРѕРїРѕР»РЅРµРЅРёСЋ: 'any', 'yes' (РґРµР»Р°Р»), 'no' (РЅРµ РґРµР»Р°Р»)
    first_topup_filter = Column(String(10), nullable=False, default='any')

    # Р РµР¶РёРј С„РёР»СЊС‚СЂР° РїСЂРѕРјРѕ-РіСЂСѓРїРї: 'all' (РІСЃРµ РІРёРґСЏС‚), 'selected' (С‚РѕР»СЊРєРѕ РІС‹Р±СЂР°РЅРЅС‹Рµ)
    promo_group_filter_mode = Column(String(20), nullable=False, default='all')

    # M2M СЃРІСЏР·СЊ СЃ РїСЂРѕРјРѕРіСЂСѓРїРїР°РјРё
    allowed_promo_groups = relationship(
        'PromoGroup',
        secondary=payment_method_promo_groups,
        lazy='selectin',
    )

    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<PaymentMethodConfig method_id='{self.method_id}' order={self.sort_order} enabled={self.is_enabled}>"


class RequiredChannel(Base):
    """Channels that users must subscribe to in order to use the bot."""

    __tablename__ = 'required_channels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String(100), unique=True, nullable=False)  # -100xxx numeric format (always string)
    channel_link = Column(String(500), nullable=True)  # https://t.me/xxx
    title = Column(String(255), nullable=True)  # Display name
    is_active = Column(Boolean, nullable=False, server_default='true')
    sort_order = Column(Integer, nullable=False, server_default='0')
    disable_trial_on_leave = Column(Boolean, nullable=False, server_default='true')
    disable_paid_on_leave = Column(Boolean, nullable=False, server_default='false')
    created_at = Column(AwareDateTime(), nullable=False, server_default=func.now())
    updated_at = Column(AwareDateTime(), nullable=True, onupdate=func.now())

    def __repr__(self) -> str:
        return f'<RequiredChannel id={self.id} channel_id={self.channel_id!r} active={self.is_active}>'


class UserChannelSubscription(Base):
    """Cache of user subscription status per required channel."""

    __tablename__ = 'user_channel_subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, nullable=False)
    channel_id = Column(String(100), nullable=False)  # matches RequiredChannel.channel_id
    is_member = Column(Boolean, nullable=False, server_default='false')
    checked_at = Column(AwareDateTime(), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('telegram_id', 'channel_id', name='uq_user_channel_sub'),
        # UniqueConstraint creates its own index; only add telegram_id index for
        # "get all subs for user" queries
        Index('ix_user_channel_sub_telegram_id', 'telegram_id'),
        # Standalone channel_id index for delete_channel() bulk DELETE
        Index('ix_user_channel_sub_channel_id', 'channel_id'),
    )

    def __repr__(self) -> str:
        return (
            f'<UserChannelSubscription telegram_id={self.telegram_id}'
            f' channel={self.channel_id!r} member={self.is_member}>'
        )


# в”Ђв”Ђ RBAC / ABAC models в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ


class AdminRole(Base):
    """Role definition with permission groups for admin cabinet RBAC."""

    __tablename__ = 'admin_roles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    level = Column(Integer, default=0, nullable=False)
    permissions = Column(JSONB, default=list, nullable=False)
    color = Column(String(7), nullable=True)
    icon = Column(String(50), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(AwareDateTime(), server_default=func.now())
    updated_at = Column(AwareDateTime(), server_default=func.now(), onupdate=func.now())

    creator = relationship('User', foreign_keys=[created_by])
    user_roles = relationship('UserRole', back_populates='role')

    def __repr__(self) -> str:
        return f'<AdminRole id={self.id} name={self.name!r} level={self.level}>'


class UserRole(Base):
    """M2M assignment of users to admin roles."""

    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('admin_roles.id', ondelete='CASCADE'), nullable=False)
    assigned_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    assigned_at = Column(AwareDateTime(), server_default=func.now())
    expires_at = Column(AwareDateTime(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='uq_user_role'),)

    user = relationship('User', foreign_keys=[user_id], back_populates='admin_roles_rel')
    role = relationship('AdminRole', back_populates='user_roles')
    assigner = relationship('User', foreign_keys=[assigned_by])

    def __repr__(self) -> str:
        return f'<UserRole id={self.id} user_id={self.user_id} role_id={self.role_id}>'


class AccessPolicy(Base):
    """ABAC attribute-based access policy."""

    __tablename__ = 'access_policies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    role_id = Column(Integer, ForeignKey('admin_roles.id', ondelete='CASCADE'), nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    effect = Column(String(10), nullable=False)  # "allow" / "deny"
    conditions = Column(JSONB, default=dict, nullable=False)
    resource = Column(String(100), nullable=False)
    actions = Column(JSONB, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(AwareDateTime(), server_default=func.now())
    updated_at = Column(AwareDateTime(), server_default=func.now(), onupdate=func.now())

    role = relationship('AdminRole')
    creator = relationship('User', foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f'<AccessPolicy id={self.id} name={self.name!r} effect={self.effect!r}>'


class AdminAuditLog(Base):
    """Immutable audit log for admin actions."""

    __tablename__ = 'admin_audit_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(20), nullable=False)
    request_method = Column(String(10), nullable=True)
    request_path = Column(Text, nullable=True)
    created_at = Column(AwareDateTime(), server_default=func.now())

    __table_args__ = (
        Index('ix_admin_audit_user_created', 'user_id', 'created_at'),
        Index('ix_admin_audit_resource', 'resource_type', 'resource_id'),
        Index('ix_admin_audit_created', 'created_at'),
    )

    user = relationship('User', foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f'<AdminAuditLog id={self.id} action={self.action!r} status={self.status!r}>'


