
import { useEffect, useState } from "react";
import API from "./services/api";
import "./App.css";

type Report = {
  report_type: string;
  generated_at: string;
  handover: {
    id: number;
    title: string;
    status: string;
  };
  project: {
    id: number;
    name: string;
    description: string | null;
    status: string;
  };
  summary: {
    total_project_items: number;
    total_evidence_links: number;
    verified_evidence_count: number;
    pending_evidence_count: number;
    items_without_linked_evidence: number;
  };
  decisions: Array<any>;
  risks_and_blockers: Array<any>;
  next_actions: Array<any>;
  evidence: {
    verified: Array<any>;
    pending_review: Array<any>;
  };
};

type UploadedDocument = {
  document_id: number;
  filename: string;
  status: string;
};







function App() {
  const HANDOVER_ID = 1;

 
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [documentMessage, setDocumentMessage] = useState("");
  const [backendStatus, setBackendStatus] = useState("Checking...");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("Overview");
  const [reviewItems, setReviewItems] = useState<any[]>([]);

  useEffect(() => {
    API.get("/health")
      .then(() => setBackendStatus("Connected"))
      .catch(() => setBackendStatus("Offline"));

    loadReviewItems();
  }, []);

  const loadReviewItems = async () => {
    try {
      const response = await API.get(
        `/review/handovers/${HANDOVER_ID}/items`
      );
      setReviewItems(response.data.items || []);
    } catch {
      setReviewItems([]);
    }
  };




  const uploadDocument = async () => {
  if (!selectedFile) {
    setDocumentMessage("Please select a document first.");
    return;
  }

  setUploading(true);
  setDocumentMessage("");

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const response = await API.post(
      "/documents/upload?project_id=1",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    const uploaded = response.data;

    setDocuments((previous) => [
      {
        document_id: uploaded.document_id,
        filename: uploaded.filename,
        status: uploaded.status,
      },
      ...previous,
    ]);

    setSelectedFile(null);
    setDocumentMessage("Document uploaded successfully!");
  } catch (err: any) {
    setDocumentMessage(
      err.response?.data?.detail || "Document upload failed."
    );
  } finally {
    setUploading(false);
  }
};

const processDocument = async (documentId: number) => {
  setProcessingId(documentId);
  setDocumentMessage("");

  try {
    await API.post(`/extraction/${documentId}`);

    setDocuments((previous) =>
      previous.map((document) =>
        document.document_id === documentId
          ? { ...document, status: "processed" }
          : document
      )
    );

    setDocumentMessage("Document extraction completed successfully!");
  } catch (err: any) {
    setDocumentMessage(
      err.response?.data?.detail || "Document extraction failed."
    );
  } finally {
    setProcessingId(null);
    }
  };

  const generateReport = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await API.post(
        `/handovers/${HANDOVER_ID}/generate`
      );

      setReport(response.data.report);
      setActiveTab("Overview");
      await loadReviewItems();
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        "Unable to generate the handover report. Check the backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = async () => {
    setError("");

    try {
      const response = await API.get(
        `/handovers/${HANDOVER_ID}/pdf`,
        { responseType: "blob" }
      );

      const fileURL = window.URL.createObjectURL(
        new Blob([response.data], { type: "application/pdf" })
      );

      const link = document.createElement("a");
      link.href = fileURL;
      link.download = `KnowFlow_Handover_${HANDOVER_ID}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(fileURL);
    } catch {
      setError("PDF download failed. Generate the report first.");
    }
  };

  const navigation = [
    { name: "Overview", icon: "◫" },
    { name: "Decisions", icon: "◇" },
    { name: "Risks & Blockers", icon: "⚠" },
    { name: "Evidence Review", icon: "◈" },
    { name: "Next Actions", icon: "☑" },
    { name: "Documents", icon: "▤" },
  ];

  const renderItems = (items: any[], emptyMessage: string) => {
    if (!items || items.length === 0) {
      return <div className="empty-state">{emptyMessage}</div>;
    }

    return items.map((item, index) => (
      <div className="record-card" key={item.id || index}>
        <div className="record-top">
          <h3>{item.title || "Untitled item"}</h3>
          <span className="tag">
            {item.type || "Project item"}
          </span>
        </div>
        <p>{item.description || "No description provided."}</p>
        <div className="record-meta">
          <span>Owner: {item.owner || "Unassigned"}</span>
          <span>Status: {item.status || "Not specified"}</span>
          <span>Priority: {item.priority || "Not specified"}</span>
        </div>
      </div>
    ));
  };

  const renderEvidence = () => {
    const items = reviewItems.length
      ? reviewItems
      : [
          ...(report?.evidence.verified || []),
          ...(report?.evidence.pending_review || []),
        ];

    if (!items.length) {
      return (
        <div className="empty-state">
          No linked evidence found. Generate a report or attach evidence
          through the review API.
        </div>
      );
    }

    return items.map((item, index) => {
      const evidence = item.evidence || {};
      const projectItem = item.project_item || {};

      return (
        <div className="record-card" key={item.handover_item_id || index}>
          <div className="record-top">
            <h3>{projectItem.title || "Linked project item"}</h3>
            <span className={`status-tag ${item.is_verified || item.verified ? "verified" : "pending"}`}>
              {item.is_verified || item.verified ? "Verified" : "Pending review"}
            </span>
          </div>

          <p>
            Source: {evidence.filename || "Source unavailable"}
          </p>
          <div className="record-meta">
            <span>Page: {evidence.page_number ?? "N/A"}</span>
            <span>Evidence ID: {evidence.id ?? "N/A"}</span>
          </div>

          {item.notes && (
            <div className="review-note">
              <strong>Reviewer notes:</strong> {item.notes}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">K</div>
          <div>
            <h2>KnowFlow</h2>
            <span>Knowledge Intelligence</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav>
          {navigation.map((item) => (
            <button
              key={item.name}
              className={`nav-item ${activeTab === item.name ? "active" : ""}`}
              onClick={() => setActiveTab(item.name)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.name}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="backend-indicator">
            <span
              className={`status-dot ${
                backendStatus === "Connected" ? "online" : "offline"
              }`}
            />
            <div>
              <strong>Backend API</strong>
              <small>{backendStatus}</small>
            </div>
          </div>
          <p>KnowFlow Hackathon Build</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace / Project</span>
            <h1>{activeTab}</h1>
          </div>

          <div className="topbar-right">
            <span className="environment-tag">DEMO PROJECT</span>
            <div className="avatar">K</div>
          </div>
        </header>

        <section className="page-content">
          <div className="welcome-section">
            <div>
              <span className="eyebrow">PROJECT WORKSPACE</span>
              <h2>
                {report?.project.name || "KnowFlow Demo Project"}
              </h2>
              <p>
                {report?.project.description ||
                  "Manage project knowledge, evidence and team handovers."}
              </p>
            </div>

            <div className="action-buttons">
              <button
                className="secondary-button"
                onClick={downloadPDF}
                disabled={!report}
              >
                ↓ Download PDF
              </button>
              <button
                className="primary-button"
                onClick={generateReport}
                disabled={loading || backendStatus !== "Connected"}
              >
                {loading ? "Generating..." : "✦ Generate Handover"}
              </button>
            </div>
          </div>

          {error && <div className="error-banner">{error}</div>}

          {!report && (
            <div className="initial-banner">
              <div>
                <strong>Your handover workspace is ready.</strong>
                <p>
                  Generate the report to load live project information
                  and evidence from your database.
                </p>
              </div>
              <button
                className="primary-button"
                onClick={generateReport}
                disabled={loading || backendStatus !== "Connected"}
              >
                {loading ? "Generating..." : "Generate first report"}
              </button>
            </div>
          )}

          {report && (
            <>


{activeTab === "Documents" && (
  <div className="panel">
    <div className="panel-heading">
      <div>
        <h3>Document Management</h3>
        <p>Upload and process project knowledge documents</p>
      </div>
      <span className="tag">Project ID: 1</span>
    </div>

    <div className="upload-area">
      <div className="upload-symbol">↑</div>
      <h3>Upload project documents</h3>
      <p>Supported formats: PDF, DOCX, CSV and TXT</p>
      <p>Maximum file size: 10 MB</p>

      <input
        type="file"
        accept=".pdf,.docx,.csv,.txt"
        onChange={(event) =>
          setSelectedFile(event.target.files?.[0] || null)
        }
      />

      {selectedFile && (
        <p className="selected-file">
          Selected: {selectedFile.name}
        </p>
      )}

      <button
        className="primary-button"
        onClick={uploadDocument}
        disabled={!selectedFile || uploading}
      >
        {uploading ? "Uploading..." : "Upload Document"}
      </button>
    </div>

    {documentMessage && (
      <div className="document-message">
        {documentMessage}
      </div>
    )}

    <div className="panel-heading document-list-heading">
      <div>
        <h3>Uploaded Documents</h3>
        <p>Documents uploaded during this session</p>
      </div>
      <span className="count-badge">{documents.length}</span>
    </div>

    {documents.length === 0 ? (
      <div className="empty-state">
        No documents uploaded during this session.
      </div>
    ) : (
      documents.map((document) => (
        <div className="record-card document-row" key={document.document_id}>
          <div className="document-info">
            <div className="file-icon">DOC</div>
            <div>
              <h3>{document.filename}</h3>
              <p>Document ID: {document.document_id}</p>
              <span className="status-tag verified">
                {document.status}
              </span>
            </div>
          </div>

          <button
            className="primary-button"
            onClick={() => processDocument(document.document_id)}
            disabled={processingId === document.document_id}
          >
            {processingId === document.document_id
              ? "Processing..."
              : "Extract Content"}
          </button>
        </div>
      ))
    )}
  </div>
)}

              {activeTab === "Overview" && (
                <>
                  <div className="section-heading">
                    <div>
                      <h2>Project overview</h2>
                      <p>Live information from your KnowFlow backend</p>
                    </div>
                    <span className="live-tag">● Live data</span>
                  </div>

                  <div className="stats-grid">
                    <div className="stat-card">
                      <span className="stat-icon purple">▣</span>
                      <p>Project Items</p>
                      <h2>{report.summary.total_project_items}</h2>
                    </div>
                    <div className="stat-card">
                      <span className="stat-icon blue">◈</span>
                      <p>Evidence Links</p>
                      <h2>{report.summary.total_evidence_links}</h2>
                    </div>
                    <div className="stat-card">
                      <span className="stat-icon green">✓</span>
                      <p>Verified Evidence</p>
                      <h2>{report.summary.verified_evidence_count}</h2>
                    </div>
                    <div className="stat-card">
                      <span className="stat-icon orange">◷</span>
                      <p>Pending Review</p>
                      <h2>{report.summary.pending_evidence_count}</h2>
                    </div>
                  </div>

                  <div className="content-grid">
                    <div className="panel">
                      <div className="panel-heading">
                        <div>
                          <h3>Project decisions</h3>
                          <p>Recorded project decisions</p>
                        </div>
                        <span className="count-badge">
                          {report.decisions.length}
                        </span>
                      </div>
                      {renderItems(
                        report.decisions,
                        "No project decisions recorded."
                      )}
                    </div>

                    <div className="panel">
                      <div className="panel-heading">
                        <div>
                          <h3>Evidence status</h3>
                          <p>Human verification summary</p>
                        </div>
                      </div>
                      <div className="evidence-summary">
                        <div>
                          <span className="summary-number green-text">
                            {report.summary.verified_evidence_count}
                          </span>
                          <span>Verified</span>
                        </div>
                        <div>
                          <span className="summary-number orange-text">
                            {report.summary.pending_evidence_count}
                          </span>
                          <span>Pending</span>
                        </div>
                        <div>
                          <span className="summary-number">
                            {report.summary.items_without_linked_evidence}
                          </span>
                          <span>Missing links</span>
                        </div>
                      </div>
                      <button
                        className="text-button"
                        onClick={() => setActiveTab("Evidence Review")}
                      >
                        View evidence →
                      </button>
                    </div>
                  </div>

                  <div className="panel full-panel">
                    <div className="panel-heading">
                      <div>
                        <h3>Recent handover</h3>
                        <p>Generated project knowledge report</p>
                      </div>
                      <span className="status-tag verified">Generated</span>
                    </div>
                    <div className="handover-row">
                      <div className="file-icon">PDF</div>
                      <div className="handover-details">
                        <strong>{report.handover.title}</strong>
                        <span>
                          Generated {new Date(report.generated_at).toLocaleString()}
                        </span>
                      </div>
                      <button
                        className="secondary-button"
                        onClick={downloadPDF}
                      >
                        Download
                      </button>
                    </div>
                  </div>
                </>
              )}

              {activeTab === "Decisions" && (
                <div className="panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Project decisions</h3>
                      <p>Decisions stored in the project database</p>
                    </div>
                  </div>
                  {renderItems(report.decisions, "No decisions found.")}
                </div>
              )}

              {activeTab === "Risks & Blockers" && (
                <div className="panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Risks and blockers</h3>
                      <p>Identified project risks and blockers</p>
                    </div>
                  </div>
                  {renderItems(
                    report.risks_and_blockers,
                    "No risks or blockers recorded."
                  )}
                </div>
              )}

              {activeTab === "Evidence Review" && (
                <div className="panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Evidence review</h3>
                      <p>Source documents and human verification status</p>
                    </div>
                    <button className="secondary-button" onClick={loadReviewItems}>
                      Refresh
                    </button>
                  </div>
                  {renderEvidence()}
                </div>
              )}

              {activeTab === "Next Actions" && (
                <div className="panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Next actions</h3>
                      <p>Outstanding project items requiring attention</p>
                    </div>
                  </div>
                  {renderItems(
                    report.next_actions,
                    "No outstanding actions found."
                  )}
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
