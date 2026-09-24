from app.services.public_lead_details import extract_lead_details


def test_extracts_request_amount_income_and_timeline_without_phone_number():
    amount, enquiry, details = extract_lead_details([
        "I need a personal loan of Rs. 10 lakhs within 3 months",
        "My monthly salary is ₹75,000",
        "9876543210",
    ], "Personal Loan", "I need a personal loan of Rs. 10 lakhs within 3 months\nProduct of interest: Personal Loan")
    assert amount == 1_000_000
    assert "personal loan" in enquiry
    assert details["stated_income"] == 75_000
    assert details["timeline_as_shared"] == "within 3 months"


def test_plain_numbers_are_not_treated_as_amounts():
    amount, _, details = extract_lead_details(["Call me on 9876543210", "I need a home loan"], "Home Loan")
    assert amount is None and "amount_as_shared" not in details
