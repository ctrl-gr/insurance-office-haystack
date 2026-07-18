from decimal import Decimal

from .company import CompanySpec
from .coverage import Deductible, Guarantee, Money, PolicyCoverage

G = Guarantee

SPEC = CompanySpec(
    company_id="blue", company_name="The Blue Company", port=5082,
    auto_rate=Decimal("0.040"), auto_young_factor=Decimal("1.35"), auto_senior_factor=Decimal("1.15"),
    home_rate=Decimal("0.0022"), life_rates=(Decimal("0.0035"), Decimal("0.009"), Decimal("0.020")),
    coverages={
        "auto": PolicyCoverage("auto", (
            G("third_party_liability", "Third party liability", "Liability for damage caused to third parties.", limit=Money(15_000_000)),
            G("theft_fire", "Theft and fire", "Loss or damage caused by theft, attempted theft, or fire."),
            G("natural_events", "Natural events", "Damage caused by covered weather and natural events."),
            G("windshield", "Windshield coverage", "Repair or replacement of insured vehicle glass."),
            G("roadside_assistance", "24h roadside assistance", "Roadside recovery and assistance available 24 hours a day."),
            G("replacement_car", "Replacement car", "Replacement vehicle following a covered claim.", terms="Up to 30 days"),
            G("mechanical_breakdown", "Mechanical breakdown", "Failure caused by mechanical or electrical breakdown.", status="excluded"),
            G("racing", "Racing events", "Use during races, speed trials, or competitive events.", status="excluded"),
        ), Deductible(Money(300))),
        "home": PolicyCoverage("home", (
            G("fire_explosion", "Fire and explosion", "Damage caused by fire, smoke, or explosion."),
            G("theft_vandalism", "Theft and vandalism", "Theft of insured property and malicious damage."),
            G("water_damage", "Water damage", "Sudden and accidental escape of water."),
            G("natural_disasters", "Natural disasters", "Damage caused by covered natural disasters."),
            G("third_party_liability", "Third party liability", "Liability arising from ownership of the home.", limit=Money(3_000_000)),
            G("temporary_accommodation", "Temporary accommodation", "Temporary housing after an insured event makes the home uninhabitable.", limit=Money(5_000)),
            G("gradual_deterioration", "Gradual deterioration", "Damage caused by gradual deterioration or poor maintenance.", status="excluded"),
            G("war_terrorism", "War and terrorism", "Loss connected with war or terrorism.", status="excluded"),
        ), Deductible(Money(200))),
        "life": PolicyCoverage("life", (
            G("death_benefit", "Death benefit", "Pays the insured capital following covered death."),
            G("total_disability", "Total permanent disability", "Benefit for covered total and permanent disability."),
            G("critical_illness", "Critical illness", "Benefit following diagnosis of one of 48 covered conditions.", terms="48 covered conditions"),
            G("accidental_death", "Accidental death double benefit", "Doubles the death benefit when death results from a covered accident.", terms="2x death benefit"),
            G("hospitalization", "Hospitalization allowance", "Daily allowance during a covered hospitalization."),
            G("pre_existing_conditions", "Pre-existing conditions", "Conditions existing before policy inception.", status="excluded", terms="Excluded during the first year"),
            G("self_inflicted_injuries", "Self-inflicted injuries", "Intentionally self-inflicted injury or death.", status="excluded"),
        )),
    },
    standard_notes={"auto": "Standard rate applied", "home": "Enhanced home insurance with temporary accommodation"},
)
