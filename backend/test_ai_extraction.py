from app.services.ai_extraction import extract_project_information

sample_evidence = [
    {
        "evidence_id": 999,
        "document_id": 999,
        "page_number": 1,
        "content": (
            "The KnowFlow frontend integration is blocked "
            "because the backend API endpoint is not connected. "
            "The backend team must complete the endpoint by "
            "15 November 2026."
        )
    }
]

result = extract_project_information(sample_evidence)

print("\nAI EXTRACTION RESULT:")
print(result)