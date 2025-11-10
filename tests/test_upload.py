from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_csv_simple():
    csv_content = "name,score\nAlice,90\nBob,85\n"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    resp = client.post("/upload-csv", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Basic shape assertions
    assert data.get("filename") == "test.csv"
    assert data.get("columns") == ["name", "score"]
    assert isinstance(data.get("rows"), list)
    assert "upload_id" in data
    upload_id = data["upload_id"]

    # Retrieve it via the retrieval endpoint
    get_resp = client.get(f"/dataframes/{upload_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data.get("filename") == "test.csv"
    assert get_data.get("columns") == ["name", "score"]

    # List stored dataframes
    list_resp = client.get("/dataframes")
    assert list_resp.status_code == 200
    items = list_resp.json().get("items", [])
    assert any(it["upload_id"] == upload_id for it in items)

    # Delete and ensure it's gone
    del_resp = client.delete(f"/dataframes/{upload_id}")
    assert del_resp.status_code == 200
    assert client.get(f"/dataframes/{upload_id}").status_code == 404
