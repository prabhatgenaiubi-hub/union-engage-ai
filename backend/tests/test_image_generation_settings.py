def test_image_generation_defaults_off_and_can_be_toggled(client,admin_headers):
    settings=client.get("/api/admin/ai-settings",headers=admin_headers)
    assert settings.status_code==200
    assert settings.json()["image_generation"]["enabled"] is False

    enabled=client.patch("/api/admin/ai-settings/image-generation",headers=admin_headers,json={"enabled":True})
    assert enabled.status_code==200
    assert enabled.json()["enabled"] is True
    assert enabled.json()["model"]=="flux1-schnell-fp8.safetensors"

    persisted=client.get("/api/admin/ai-settings",headers=admin_headers)
    assert persisted.json()["image_generation"]["enabled"] is True

def test_image_generation_setting_requires_admin(client,customer_headers):
    response=client.patch("/api/admin/ai-settings/image-generation",headers=customer_headers,json={"enabled":True})
    assert response.status_code==403
