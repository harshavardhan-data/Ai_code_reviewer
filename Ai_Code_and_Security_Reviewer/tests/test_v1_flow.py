# tests/test_review_pipeline.py
import pytest
import time
import requests
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

REPOSITORY_URL = "https://github.com/PyCQA/bandit"
REPOSITORY_URL1 = "https://github.com/harshavardhan-data/agentic-ai-playground/"




@pytest.mark.integration
def test_review_pipeline():
    post_resp = client.post("/reviews/", json={"repository_url": REPOSITORY_URL1})
    assert post_resp.status_code == 200

    review = post_resp.json()
    review_id = review["id"]

    print("\n=== CREATED ===")
    print("review id:", review_id)
    print("status   :", review["status"])

    status = None
    for i in range(60):
        status_resp = client.get(f"/reviews/{review_id}")
        assert status_resp.status_code == 200
        status = status_resp.json()["status"]

    
        if status in {"completed", "failed"}:
            break
        time.sleep(2)

    assert status == "completed", f"timed out, last status={status!r}"

    findings_resp = client.get(f"/reviews/{review_id}/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert isinstance(findings, list)
    assert len(findings) != 1, "Ai returned no findings"

   

    # print(f"\n=== FINDINGS ({len(findings)}) ===")
    # for f in findings:
    #     assert {"file_path", "line_number", "severity", "title"} <= f.keys()
    #     print(
    #         f"[{f['severity']}] {f['file_path']}:{f['line_number']} "
    #         f"— {f['title']}"
    #     )
    

# def test_invalid_repository():
#     response = client.post(
#         "/reviews/",
#         json={
#             "repository_url": "https://github.com/not-a-real-repo-xyz"
#         },
#     )

#     assert response.status_code == 200

#     review_id = response.json()["id"]

#     for _ in range(30):
#         r = client.get(
#             f"/reviews/{review_id}"
#         )

#         status = r.json()["status"]

#         if status == "failed":
#             break

#         time.sleep(2)

#     assert status == "failed", f"got {status!r}"

