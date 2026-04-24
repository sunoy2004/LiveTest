from __future__ import annotations


class GamificationError(Exception):
    pass


class RuleNotFoundError(GamificationError):
    def __init__(self, rule_code: str):
        self.rule_code = rule_code
        super().__init__(rule_code)


class RuleInactiveError(GamificationError):
    def __init__(self, rule_code: str):
        self.rule_code = rule_code
        super().__init__(rule_code)


class CooldownActiveError(GamificationError):
    pass


class InsufficientFundsError(GamificationError):
    pass


class InvalidAmountError(GamificationError):
    pass
