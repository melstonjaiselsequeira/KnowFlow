
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    JSON,
    func,
)
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50))
    file_path = Column(Text)
    processing_status = Column(String(50), default="pending")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer)
    chunk_index = Column(Integer)
    metadata_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProjectItem(Base):
    __tablename__ = "project_items"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    item_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    owner = Column(String(255))
    status = Column(String(50), default="open")
    priority = Column(String(50))
    due_date = Column(DateTime(timezone=True))
    confidence = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Handover(Base):
    __tablename__ = "handovers"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(JSON)
    status = Column(String(50), default="draft")
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HandoverItem(Base):
    __tablename__ = "handover_items"

    id = Column(Integer, primary_key=True, index=True)
    handover_id = Column(Integer, ForeignKey("handovers.id"), nullable=False)
    project_item_id = Column(Integer, ForeignKey("project_items.id"))
    evidence_chunk_id = Column(Integer, ForeignKey("evidence_chunks.id"))
    notes = Column(Text)
    is_verified = Column(Boolean, default=False)
