import enum
from typing import Optional

from pydantic import Field, root_validator, validator, BaseModel
import enum
from typing import Optional, Union
from furl import furl
from decimal import Decimal


# Models
class Model(BaseModel):
    """Generic dashboards-specific model."""

    class Config:
        # To make it work with Arrow type
        arbitrary_types_allowed = True
        # For fields that defined with their aliases, we allow population
        # by their field names as well, for compatibility with
        # our caching mechanism.
        allow_population_by_field_name = True


class FrozenModel(BaseModel):
    """Generic dashboards-specific frozen model."""

    class Config:
        # To make it work with Arrow type
        arbitrary_types_allowed = True
        # Make it frozen to allow using as dict keys
        frozen = True
        # For fields that defined with their aliases, we allow population
        # by their field names as well, for compatibility with
        # our caching mechanism.
        allow_population_by_field_name = True

# Currencies

def ethereum_like(code: str, name: str):
    """Constructor for ethereum-like currencies."""
    return dict(
        code=code,
        precision=18,
        name=name,
        type="CRYPTO",
    )


# Currency constructors.
CURRENCIES = {
    "USD": dict(code="USD", precision=8, name="US Dollar", type="FIAT", symbol="$"),
    "EUR": dict(code="EUR", precision=8, name="Euro", type="FIAT", symbol="\u20AC"),
    "BTC": dict(
        code="BTC",
        precision=8,
        name="Bitcoin",
        type="CRYPTO",
        symbol="\u20BF",
    ),
    "ETH": ethereum_like("ETH", "Ether"),
    "ELLA": ethereum_like("ELLA", "Ellaism Token"),
    "EWT": ethereum_like("EWT", "Energy Web Token"),
    "POA": ethereum_like("POA", "POA Network Token"),
    "DAI": ethereum_like("DAI", "Dai Token"),
    "TLN": ethereum_like("TLN", "Trustlines Network Token"),
    "PAN": ethereum_like("PAN", "Panvala Token"),
    "LINK": ethereum_like("LINK", "Link Token"),
}

# All known fractions for currencies. Consider this as a crypto-specific fraction
# name mapping without connections to specific currencies: such as
# "kilo" or "milli" in physics.
FRACTIONS = {
    "base": Decimal("1"),
    "wei": Decimal("0.000000000000000001"),
    "gwei": Decimal("0.000000001"),
    "satoshi": Decimal("0.00000001"),
}



# Currency interface

class CurrencyType(enum.Enum):
    CRYPTO = "CRYPTO"
    FIAT = "FIAT"


class Currency(FrozenModel):
    """Currency representation."""

    code: str
    precision: int
    name: str
    type: CurrencyType
    symbol: Optional[str] = Field(default=None)

    def __repr__(self):
        return f"Currency({self})"

    def __str__(self):
        return self.code

    def __mul__(self, other):
        if isinstance(other, (int, Decimal)):
            return CurrencyAmount(amount=Decimal(other), currency=self)
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, (int, Decimal)):
            return CurrencyAmount(amount=Decimal(other), currency=self)
        return NotImplemented

    @property
    def zero(self) -> "CurrencyAmount":
        """Zero items of that currency."""
        return 0 * self

    @property
    def one(self) -> "CurrencyAmount":
        """One item of that currency."""
        return 1 * self

    @property
    def symbol_or_code(self):
        return self.symbol or self.code

    @property
    def name_plural(self):
        return self.name + "s"

    @classmethod
    def from_code(cls, code: str):
        return Currency(**CURRENCIES[code.upper()])

    def dict(self, *args, **kwargs):
        """
        Serialize currency

        BaseModel.dict() is called by BaseModel.json(). Therefore, when caching the
        value, we always store only the code, instead of serializing the entire object.
        """
        return {"code": self.code}

    @root_validator(pre=True)
    def restore_from_code(cls, values):
        """
        The operation, opposite of serialization.

        If the caller provided only the code, restore the value, using ALL_CURRENCIES
        """
        only_code = list(values.keys()) == ["code"]
        if only_code:
            return CURRENCIES[values["code"]]
        return values

    @property
    def minimal_value(self):
        """Return the minimal value that can be represented by that currency."""
        return Decimal("1") / (10 ** self.precision)

    def get_amount(self, amount: Union[Decimal, int]) -> "CurrencyAmount":
        """Return currency amount."""
        return CurrencyAmount(amount=Decimal(amount), currency=self)

    def get_fraction(self, fraction_name: str) -> "CurrencyFraction":
        """Return a currency fraction."""
        if fraction_name not in FRACTIONS:
            raise RuntimeError(f"{fraction_name} is not known")
        return CurrencyFraction(
            currency=self, name=fraction_name, multiplier=FRACTIONS[fraction_name]
        )


class CurrencyFraction(FrozenModel):
    """Currency fraction."""

    currency: Currency
    name: str
    multiplier: Decimal

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"CurrencyFraction({self})"

    def __mul__(self, other):
        if isinstance(other, (int, float, Decimal)):
            return self.get_amount(Decimal(other))
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, (int, float, Decimal)):
            return self.get_amount(Decimal(other))
        return NotImplemented

    def get_amount(self, amount: Union[int, float, Decimal]) -> "CurrencyAmount":
        """Return currency amount."""
        return self.currency.get_amount(Decimal(amount) * self.multiplier)


class CurrencyAmount(FrozenModel):
    """Currency amount representation."""

    currency: Currency
    amount: Decimal

    def __str__(self):
        return f"{self.amount} {self.currency}"

    def __repr__(self):
        return f"CurrencyAmount({self})"

    def __add__(self, other):
        if isinstance(other, CurrencyAmount):
            if self.currency == other.currency:
                return CurrencyAmount(
                    amount=self.amount + other.amount, currency=self.currency
                )
            raise TypeError(
                f"Amounts have different currencies: {self.currency} "
                f"and {other.currency}"
            )
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, CurrencyAmount):
            if self.currency == other.currency:
                return CurrencyAmount(
                    amount=self.amount - other.amount, currency=self.currency
                )
            raise TypeError(
                f"Amounts have different currencies: {self.currency} "
                f"and {other.currency}"
            )
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, (int, Decimal)):
            return CurrencyAmount(amount=other * self.amount, currency=self.currency)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, (int, Decimal)):
            return CurrencyAmount(amount=self.amount / other, currency=self.currency)
        return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, (int, Decimal)):
            return CurrencyAmount(amount=self.amount // other, currency=self.currency)
        return NotImplemented

    @validator("amount")
    def quantize_amount(cls, value: Decimal, values: dict):
        currency: Currency = values["currency"]
        return value.quantize(currency.minimal_value)

    @classmethod
    def from_fraction(cls, amount: Decimal, currency: Currency, fraction_name: str):
        """
        Create a currency amount from fraction

        Args:
            amount: amount in fraction units. E.g., 25
            currency: base currency, E.g. ETH object for Ethereum
            fraction_name: fraction name. Must be a registered fraction name for
                the currency. E.g., "wei"

        Returns:
            Correct currency of the specific amount.
        """
        fraction = currency.get_fraction(fraction_name)
        amount_base = (amount * fraction.multiplier).quantize(currency.minimal_value)
        return CurrencyAmount(amount=amount_base, currency=currency)

    def as_fraction(self, fraction_name: str) -> Decimal:
        """Convert currency amount to fraction value."""
        fraction = self.currency.get_fraction(fraction_name)
        return self.amount / fraction.multiplier


# Networks
class NetworkRole(enum.Enum):
    MAINNET = "MAINNET"
    TESTNET = "TESTNET"


class Network(FrozenModel):
    """A blockchain network representation."""

    technology: str = Field(description="Network technology. E.g., 'ethereum'")
    blockchain: str = Field(description="Network blockchain. E.g., 'ethereum'")
    network: str = Field(description="Network name. E.g., 'mainnet'")
    role: NetworkRole = Field(description="Network role. Can be MAINNET or TESTNET")
    title: str = Field(
        description="Human-readable network name. E.g., 'Ethereum Mainnet'"
    )
    currency: Optional[Currency] = Field(
        default=None,
        description="Currency of the network. Makes sense only for non-test networks.",
    )

    @property
    def key(self):
        """Unique network-specific key that we may use internally."""
        return f"{self.technology}/{self.blockchain}/{self.network}"

    @property
    def icon_url(self) -> str:
        """
        Icon component for the network.

        See https://apidocs.anyblock.tools/#/Public/blockchain-icon for
        more details

        Returns:
            Full network icon URL as a string.
        """
        return str(
            ANYBLOCK_API_ROOT = furl("https://api.anyblock.tools/")
            / self.technology
            / self.blockchain
            / self.network
            / "icon"
        )

    def __repr__(self):
        # We use custom __repr__ to use Network objects as cache keys in
        # the Flask-Cache. See https://flask-caching.readthedocs.io/en/latest/
        return f"Network({self.key})"


class NetworkRole(enum.Enum):
    MAINNET = "MAINNET"
    TESTNET = "TESTNET"


class Network(FrozenModel):
    """A blockchain network representation."""

    technology: str = Field(description="Network technology. E.g., 'ethereum'")
    blockchain: str = Field(description="Network blockchain. E.g., 'ethereum'")
    network: str = Field(description="Network name. E.g., 'mainnet'")
    role: NetworkRole = Field(description="Network role. Can be MAINNET or TESTNET")
    title: str = Field(
        description="Human-readable network name. E.g., 'Ethereum Mainnet'"
    )
    currency: Optional[Currency] = Field(
        default=None,
        description="Currency of the network. Makes sense only for non-test networks.",
    )

    @property
    def key(self):
        """Unique network-specific key that we may use internally."""
        return f"{self.technology}/{self.blockchain}/{self.network}"

    @property
    def icon_url(self) -> str:
        """
        Icon component for the network.

        See https://apidocs.anyblock.tools/#/Public/blockchain-icon for
        more details

        Returns:
            Full network icon URL as a string.
        """
        return str(
            config.ANYBLOCK_API_ROOT
            / self.technology
            / self.blockchain
            / self.network
            / "icon"
        )

    def __repr__(self):
        # We use custom __repr__ to use Network objects as cache keys in
        # the Flask-Cache. See https://flask-caching.readthedocs.io/en/latest/
        return f"Network({self.key})"
