from dataclasses import dataclass


@dataclass
class VehicleBase:
    """
    Base vehicle model. Per-day rate is the public listed price before discount.
    Subclasses are free to adjust the base price calculation.
    """
    vehicle_id: str
    brand: str
    model: str
    type: str  # "car" | "motorbike" | "truck"
    rate: float  # base rate per day

    def price_for_days(self, days: int) -> float:
        """
        Base price for the rental length *before* user discount is applied.
        Subclasses can override to add surcharges or reductions.
        """
        return self.rate * days


class Car(VehicleBase):
    """
    Cars follow the base rule.
    """
    pass


class Motorbike(VehicleBase):
    """
    Example: motorbikes are 10% cheaper than the listed daily rate.
    """

    def price_for_days(self, days: int) -> float:
        return super().price_for_days(days) * 0.9


class Truck(VehicleBase):
    """
    Example: trucks carry a 20% surcharge over the base.
    """

    def price_for_days(self, days: int) -> float:
        return super().price_for_days(days) * 1.2
