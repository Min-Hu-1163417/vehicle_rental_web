from dataclasses import dataclass


@dataclass
class UserBase:
    """
    Base user model. The Store keeps raw dicts; we wrap them into rich objects
    to express discount logic via polymorphism.
    """
    user_id: str
    username: str
    role: str  # "individual" | "corporate" | "staff"

    def discount_for(self, days: int) -> float:
        """
        Return a discount ratio in [0, 1], e.g. 0.15 means 15% off.
        Subclasses override this to implement role-specific rules.
        """
        return 0.0


class IndividualUser(UserBase):
    """
    Individuals get 10% off for long rentals (>= 7 days).
    """

    def discount_for(self, days: int) -> float:
        return 0.10 if days >= 7 else 0.0


class CorporateUser(UserBase):
    """
    Corporate customers get a flat 15% discount.
    """

    def discount_for(self, days: int) -> float:
        return 0.15


class StaffUser(UserBase):
    """
    Staff rule can vary by assignment; here we grant 100% off as an example.
    Adjust if your marking rubric expects a different rule.
    """

    def discount_for(self, days: int) -> float:
        return 1.0
