"""Curated list of official sources for the three domains.

Every entry was checked against the live site on 28 Oct 2026 (HTTP 200).
GOV.UK pages are fetched through the public Content API; NHS pages as HTML.
Both are published under the Open Government Licence v3.0, and NHS reuse
also needs attribution, a link back and a date notice (nhs.uk terms).
"""

GOVUK = {
    "schools": [
        "schools-admissions",
        "apply-for-primary-school-place",
        "apply-for-secondary-school-place",
        "school-attendance-absence",
        "apply-free-school-meals",
        "children-with-special-educational-needs",
        "free-school-transport",
        "school-uniform",
        "types-of-school",
        "school-term-holiday-dates",
        "know-when-you-can-leave-school",
        "complain-about-school",
    ],
    "housing": [
        "private-renting",
        "private-renting-evictions",
        "guidance/renters-rights-act-overview-for-tenants",
        "tenancy-deposit-protection",
        "council-housing",
        "housing-association-homes",
        "council-housing-association-evictions",
        "housing-benefit",
        "universal-credit",
        "homelessness-help-from-council",
        "council-tax",
        "apply-council-tax-reduction",
    ],
    "health": [
        "help-nhs-costs",
        "healthcare-immigration-application",
    ],
}

NHS = {
    "health": [
        "https://www.nhs.uk/nhs-services/gps/how-to-register-with-a-gp-surgery/",
        "https://www.nhs.uk/nhs-services/gps/gp-appointments-and-bookings/",
        "https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/",
        "https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-go-to-ae/",
        "https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/",
        "https://www.nhs.uk/nhs-services/dentists/how-to-find-an-nhs-dentist/",
        "https://www.nhs.uk/nhs-services/dentists/how-much-nhs-dental-treatment-costs/",
        "https://www.nhs.uk/nhs-services/pharmacies/how-pharmacies-can-help/",
        "https://www.nhs.uk/nhs-services/help-with-health-costs/nhs-low-income-scheme-lis/",
        "https://www.nhs.uk/nhs-services/visiting-or-moving-to-england/how-to-access-nhs-services-in-england-if-you-are-visiting-from-abroad/",
        "https://www.nhs.uk/vaccinations/nhs-vaccinations-and-when-to-have-them/",
        "https://www.nhs.uk/pregnancy/finding-out/what-to-do-when-you-find-out-you-are-pregnant/",
    ],
}
