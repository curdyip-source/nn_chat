from types import SimpleNamespace

from app.services import push_notifications
from app.services.push_notifications import _apns_endpoint_for_device


SANDBOX = "https://api.sandbox.push.apple.com"
PRODUCTION = "https://api.push.apple.com"


def test_endpoint_uses_sandbox_for_sandbox_device():
    device = SimpleNamespace(user_device_environment="sandbox")
    assert _apns_endpoint_for_device(device) == SANDBOX


def test_endpoint_uses_production_for_production_device():
    device = SimpleNamespace(user_device_environment="production")
    assert _apns_endpoint_for_device(device) == PRODUCTION


def test_endpoint_falls_back_to_global_flag_for_legacy_device(monkeypatch):
    device = SimpleNamespace(user_device_environment=None)

    monkeypatch.setattr(push_notifications, "APNS_USE_SANDBOX", True)
    assert _apns_endpoint_for_device(device) == SANDBOX

    monkeypatch.setattr(push_notifications, "APNS_USE_SANDBOX", False)
    assert _apns_endpoint_for_device(device) == PRODUCTION
