"""Tests for music web panel guild authorization."""

GUILD_ID = 123456789


class TestWebAuth:
    """Assert 401/403/success across read and mutating routes."""

    # ------------------------------------------------------------------
    # Unauthenticated → 401
    # ------------------------------------------------------------------

    def test_status_unauthenticated(self, unauthed_client):
        resp = unauthed_client.get(f"/api/music/status/{GUILD_ID}")
        assert resp.status_code == 401

    def test_queue_path_unauthenticated(self, unauthed_client):
        resp = unauthed_client.get(f"/api/music/queue/{GUILD_ID}")
        assert resp.status_code == 401

    def test_queue_query_unauthenticated(self, unauthed_client):
        resp = unauthed_client.get("/api/music/queue", params={"guild_id": GUILD_ID})
        assert resp.status_code == 401

    def test_play_unauthenticated(self, unauthed_client):
        resp = unauthed_client.post("/api/music/play", data={"query": "test", "guild_id": GUILD_ID})
        assert resp.status_code == 401

    def test_controls_unauthenticated(self, unauthed_client):
        resp = unauthed_client.post("/api/music/controls/skip", data={"guild_id": GUILD_ID})
        assert resp.status_code == 401

    def test_volume_unauthenticated(self, unauthed_client):
        resp = unauthed_client.post("/api/music/volume", data={"guild_id": GUILD_ID, "volume": 50})
        assert resp.status_code == 401

    def test_repeat_unauthenticated(self, unauthed_client):
        resp = unauthed_client.post("/api/music/repeat", data={"guild_id": GUILD_ID, "mode": "off"})
        assert resp.status_code == 401

    def test_shuffle_unauthenticated(self, unauthed_client):
        resp = unauthed_client.post("/api/music/shuffle", data={"guild_id": GUILD_ID})
        assert resp.status_code == 401

    def test_queue_remove_unauthenticated(self, unauthed_client):
        resp = unauthed_client.post("/api/music/queue/remove", data={"guild_id": GUILD_ID, "position": 0})
        assert resp.status_code == 401

    def test_queue_reorder_unauthenticated(self, unauthed_client):
        resp = unauthed_client.post("/api/music/queue/reorder", data={"guild_id": GUILD_ID, "from_position": 0, "to_position": 1})
        assert resp.status_code == 401

    def test_search_suggestions_unauthenticated(self, unauthed_client):
        resp = unauthed_client.get("/api/music/search/suggestions", params={"query": "test"})
        assert resp.status_code == 401

    def test_sources_unauthenticated(self, unauthed_client):
        resp = unauthed_client.get("/api/music/sources")
        assert resp.status_code == 401

    def test_panel_page_unauthenticated(self, unauthed_client):
        resp = unauthed_client.get("/plugin/music")
        assert resp.status_code == 401

    # ------------------------------------------------------------------
    # Wrong guild → 403
    # ------------------------------------------------------------------

    def test_status_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.get(f"/api/music/status/{GUILD_ID}")
        assert resp.status_code == 403

    def test_queue_path_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.get(f"/api/music/queue/{GUILD_ID}")
        assert resp.status_code == 403

    def test_play_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.post("/api/music/play", data={"query": "test", "guild_id": GUILD_ID})
        assert resp.status_code == 403

    def test_controls_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.post("/api/music/controls/skip", data={"guild_id": GUILD_ID})
        assert resp.status_code == 403

    def test_volume_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.post("/api/music/volume", data={"guild_id": GUILD_ID, "volume": 50})
        assert resp.status_code == 403

    def test_repeat_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.post("/api/music/repeat", data={"guild_id": GUILD_ID, "mode": "off"})
        assert resp.status_code == 403

    def test_shuffle_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.post("/api/music/shuffle", data={"guild_id": GUILD_ID})
        assert resp.status_code == 403

    def test_queue_remove_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.post("/api/music/queue/remove", data={"guild_id": GUILD_ID, "position": 0})
        assert resp.status_code == 403

    def test_queue_reorder_wrong_guild(self, wrong_guild_client):
        resp = wrong_guild_client.post("/api/music/queue/reorder", data={"guild_id": GUILD_ID, "from_position": 0, "to_position": 1})
        assert resp.status_code == 403

    # ------------------------------------------------------------------
    # Authorized → success (not 401/403)
    # ------------------------------------------------------------------

    def test_status_authorized(self, authed_client):
        resp = authed_client.get(f"/api/music/status/{GUILD_ID}")
        assert resp.status_code not in (401, 403)

    def test_queue_path_authorized(self, authed_client):
        resp = authed_client.get(f"/api/music/queue/{GUILD_ID}")
        assert resp.status_code not in (401, 403)

    def test_panel_page_authorized(self, authed_client):
        resp = authed_client.get("/plugin/music")
        assert resp.status_code not in (401, 403)

    def test_sources_authorized(self, authed_client):
        resp = authed_client.get("/api/music/sources")
        assert resp.status_code not in (401, 403)

    def test_search_suggestions_authorized(self, authed_client):
        resp = authed_client.get("/api/music/search/suggestions", params={"query": "test"})
        assert resp.status_code not in (401, 403)
