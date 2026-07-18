from decimal import Decimal

from .company import CompanySpec
from .coverage import Deductible, Guarantee, Money, PolicyCoverage

G = Guarantee

SPEC = CompanySpec(
    company_id="three-lines", company_name="The Three Lines Insurance", port=5083,
    auto_rate=Decimal("0.055"), auto_young_factor=Decimal("1.30"), auto_senior_factor=Decimal("1.10"),
    home_rate=Decimal("0.0028"), life_rates=(Decimal("0.0045"), Decimal("0.011"), Decimal("0.024")),
    coverages={
        "auto": PolicyCoverage("auto", (
            G("third_party_liability", "Third party liability", "Liability for damage caused to third parties.", limit=Money(25_000_000)),
            G("theft_fire", "Theft and fire", "Loss or damage caused by theft, attempted theft, or fire."),
            G("natural_events", "Natural events", "Damage caused by covered weather and natural events."),
            G("windshield", "Windshield coverage", "Repair or replacement of insured vehicle glass."),
            G("roadside_assistance", "24h roadside assistance", "Roadside recovery and assistance available 24 hours a day."),
            G("replacement_car", "Replacement car", "Replacement vehicle following a covered claim.", terms="Up to 60 days"),
            G("legal_protection", "Legal protection", "Legal assistance and covered defence costs."),
            G("personal_accident", "Personal accident coverage", "Benefit for covered bodily injury to the insured driver."),
            G("racing", "Racing events", "Use during races, speed trials, or competitive events.", status="excluded"),
        ), Deductible(Money(150))),
        "home": PolicyCoverage("home", (
            G("fire_explosion", "Fire and explosion", "Damage caused by fire, smoke, or explosion."),
            G("theft_vandalism", "Theft and vandalism", "Theft of insured property and malicious damage."),
            G("water_damage", "Water damage", "Sudden and accidental escape of water."),
            G("natural_disasters", "Natural disasters", "Damage caused by covered natural disasters."),
            G("third_party_liability", "Third party liability", "Liability arising from ownership of the home.", limit=Money(5_000_000)),
            G("temporary_accommodation", "Temporary accommodation", "Temporary housing after an insured event makes the home uninhabitable.", limit=Money(15_000)),
            G("valuables", "Valuables and jewelry", "Covered loss or damage to declared valuables and jewelry.", limit=Money(10_000)),
            G("smart_home", "Smart home devices", "Covered loss or damage to installed smart-home devices."),
            G("war_terrorism", "War and terrorism", "Loss connected with war or terrorism.", status="excluded"),
        ), Deductible(Money(100))),
        "life": PolicyCoverage("life", (
            G("death_benefit", "Death benefit", "Pays the insured capital following covered death."),
            G("total_disability", "Total permanent disability", "Benefit for covered total and permanent disability."),
            G("critical_illness", "Critical illness", "Benefit following diagnosis of one of 60 covered conditions.", terms="60 covered conditions"),
            G("accidental_death", "Accidental death triple benefit", "Triples the death benefit when death results from a covered accident.", terms="3x death benefit"),
            G("hospitalization", "Hospitalization allowance", "Daily allowance during a covered hospitalization."),
            G("rehabilitation", "Rehabilitation coverage", "Support for covered rehabilitation treatment."),
            G("mental_health", "Mental health support", "Access to covered mental-health support services."),
            G("self_inflicted_injuries", "Self-inflicted injuries", "Intentionally self-inflicted injury or death.", status="excluded"),
        )),
    },
    standard_notes={"auto": "Premium rate — full coverage", "home": "Premium home insurance — lowest deductible on market"},
)
