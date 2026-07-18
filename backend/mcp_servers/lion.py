from decimal import Decimal

from .company import CompanySpec
from .coverage import Deductible, Guarantee, Money, PolicyCoverage

G = Guarantee

SPEC = CompanySpec(
    company_id="lion", company_name="The Lion Insurance", port=5081,
    auto_rate=Decimal("0.045"), auto_young_factor=Decimal("1.40"), auto_senior_factor=Decimal("1.20"),
    home_rate=Decimal("0.002"), life_rates=(Decimal("0.003"), Decimal("0.008"), Decimal("0.018")),
    coverages={
        "auto": PolicyCoverage("auto", (
            G("third_party_liability", "Third party liability", "Liability for damage caused to third parties.", limit=Money(10_000_000)),
            G("theft_fire", "Theft and fire", "Loss or damage caused by theft, attempted theft, or fire."),
            G("natural_events", "Natural events", "Damage caused by covered weather and natural events."),
            G("windshield", "Windshield coverage", "Repair or replacement of insured vehicle glass."),
            G("roadside_assistance", "24h roadside assistance", "Roadside recovery and assistance available 24 hours a day."),
            G("mechanical_breakdown", "Mechanical breakdown", "Failure caused by mechanical or electrical breakdown.", status="excluded"),
            G("wear_and_tear", "Wear and tear", "Gradual deterioration from normal use.", status="excluded"),
            G("racing", "Racing events", "Use during races, speed trials, or competitive events.", status="excluded"),
        ), Deductible(Money(500))),
        "home": PolicyCoverage("home", (
            G("fire_explosion", "Fire and explosion", "Damage caused by fire, smoke, or explosion."),
            G("theft_vandalism", "Theft and vandalism", "Theft of insured property and malicious damage."),
            G("water_damage", "Water damage", "Sudden and accidental escape of water."),
            G("natural_disasters", "Natural disasters", "Damage caused by covered natural disasters."),
            G("third_party_liability", "Third party liability", "Liability arising from ownership of the home.", limit=Money(2_000_000)),
            G("gradual_deterioration", "Gradual deterioration", "Damage caused by gradual deterioration or poor maintenance.", status="excluded"),
            G("war_terrorism", "War and terrorism", "Loss connected with war or terrorism.", status="excluded"),
            G("nuclear_events", "Nuclear events", "Loss caused by nuclear or radioactive events.", status="excluded"),
        ), Deductible(Money(250))),
        "life": PolicyCoverage("life", (
            G("death_benefit", "Death benefit", "Pays the insured capital following covered death."),
            G("total_disability", "Total permanent disability", "Benefit for covered total and permanent disability."),
            G("critical_illness", "Critical illness", "Benefit following diagnosis of one of 36 covered conditions.", terms="36 covered conditions"),
            G("accidental_death", "Accidental death double benefit", "Doubles the death benefit when death results from a covered accident.", terms="2x death benefit"),
            G("pre_existing_conditions", "Pre-existing conditions", "Conditions existing before policy inception.", status="excluded", terms="Excluded during the first 2 years"),
            G("self_inflicted_injuries", "Self-inflicted injuries", "Intentionally self-inflicted injury or death.", status="excluded"),
            G("extreme_sports", "Extreme sports", "Participation in listed hazardous sports.", status="excluded"),
        )),
    },
    standard_notes={"auto": "Standard rate applied", "home": "Standard home insurance rate"},
)
