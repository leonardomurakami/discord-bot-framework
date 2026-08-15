"""Tests for web volume bounds (0-100)."""

GUILD_ID = 123456789


class TestWebVolume:
    """Assert values >100 are rejected and 0-100 are applied."""

    def test_volume_over_100_rejected(self, authed_client):
        """Volume > 100 should be rejected with an error message."""
        resp = authed_client.post("/api/music/volume", data={"guild_id": GUILD_ID, "volume": 150})
        assert resp.status_code == 200  # HTML response with error
        body = resp.text
        assert "must be between 0 and 100" in body

    def test_volume_150_rejected(self, authed_client):
        """Volume 150 (old max) should now be rejected."""
        resp = authed_client.post("/api/music/volume", data={"guild_id": GUILD_ID, "volume": 150})
        assert "must be between 0 and 100" in resp.text

    def test_volume_100_accepted(self, authed_client):
        """Volume 100 (max) should be applied."""
        resp = authed_client.post("/api/music/volume", data={"guild_id": GUILD_ID, "volume": 100})
        assert resp.status_code == 200
        assert "must be between" not in resp.text
        authed_client.player.set_volume.assert_called_with(100)

    def test_volume_0_accepted(self, authed_client):
        """Volume 0 (min) should be applied."""
        resp = authed_client.post("/api/music/volume", data={"guild_id": GUILD_ID, "volume": 0})
        assert resp.status_code == 200
        assert "must be between" not in resp.text
        authed_client.player.set_volume.assert_called_with(0)

    def test_volume_50_accepted(self, authed_client):
        """Volume 50 (mid) should be applied."""
        resp = authed_client.post("/api/music/volume", data={"guild_id": GUILD_ID, "volume": 50})
        assert resp.status_code == 200
        assert "must be between" not in resp.text
        authed_client.player.set_volume.assert_called_with(50)

    def test_volume_negative_rejected(self, authed_client):
        """Volume < 0 should be rejected."""
        resp = authed_client.post("/api/music/volume", data={"guild_id": GUILD_ID, "volume": -1})
        assert "must be between 0 and 100" in resp.text
