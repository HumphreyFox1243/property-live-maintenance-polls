from src.poll_service import MaintenanceRequest, poll_decision


def test_quorum_approves_maintenance_request():
    request = MaintenanceRequest(unit="A-204", issue="Leaking kitchen tap", votes=3)
    assert poll_decision(request, quorum=3) == "approved"
