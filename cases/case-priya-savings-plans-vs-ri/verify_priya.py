"""Independent arithmetic check for Priya's Module 11 case.

The script deliberately imports no application modules. Rates are the exact
public-price snapshot values documented in the team's validation evidence.
"""

from decimal import Decimal, getcontext


getcontext().prec = 28

HOURS_PER_YEAR = Decimal("8760")
EXPECTED_RUNTIME = Decimal("0.80")
ON_DEMAND_HOURLY = Decimal("0.085")
ONE_YEAR_NO_UPFRONT_RI_HOURLY = Decimal("0.05623")


def main() -> None:
    on_demand_annual = ON_DEMAND_HOURLY * HOURS_PER_YEAR * EXPECTED_RUNTIME
    ri_annual = ONE_YEAR_NO_UPFRONT_RI_HOURLY * HOURS_PER_YEAR
    modeled_saving = on_demand_annual - ri_annual
    break_even_pct = (
        ri_annual / (ON_DEMAND_HOURLY * HOURS_PER_YEAR) * Decimal("100")
    )

    print(f"On-Demand annual cost: ${on_demand_annual:.4f}")
    print(f"RI annual cost:        ${ri_annual:.4f}")
    print(f"Modeled annual saving: ${modeled_saving:.4f}")
    print(f"Break-even runtime:    {break_even_pct:.10f}%")
    print(
        "Savings Plan result:   unavailable — no Savings Plan rates or account "
        "recommendation are inputs"
    )


if __name__ == "__main__":
    main()
