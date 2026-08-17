"""Initial Schema Migration for Research Entities

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-13 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. research_projects
    op.create_table(
        "research_projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("research_topic", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_projects_name"), "research_projects", ["name"], unique=False)
    op.create_index(op.f("ix_research_projects_status"), "research_projects", ["status"], unique=False)

    # 2. research_questions
    op.create_table(
        "research_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_questions_project_id"), "research_questions", ["project_id"], unique=False)

    # 3. research_runs
    op.create_table(
        "research_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="queued", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["research_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_runs_question_id"), "research_runs", ["question_id"], unique=False)
    op.create_index(op.f("ix_research_runs_status"), "research_runs", ["status"], unique=False)

    # 4. research_sources
    op.create_table(
        "research_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("credibility_score", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_sources_research_run_id"), "research_sources", ["research_run_id"], unique=False)

    # 5. source_contents
    op.create_table(
        "source_contents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("extraction_status", sa.String(length=50), server_default="completed", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_contents_source_id"), "source_contents", ["source_id"], unique=False)

    # 6. findings
    op.create_table(
        "findings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("finding_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("importance", sa.String(length=50), server_default="medium", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_findings_finding_type"), "findings", ["finding_type"], unique=False)
    op.create_index(op.f("ix_findings_research_run_id"), "findings", ["research_run_id"], unique=False)

    # 7. evidences
    op.create_table(
        "evidences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("source_content_id", sa.UUID(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_content_id"], ["source_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidences_finding_id"), "evidences", ["finding_id"], unique=False)
    op.create_index(op.f("ix_evidences_source_content_id"), "evidences", ["source_content_id"], unique=False)
    op.create_index(op.f("ix_evidences_source_id"), "evidences", ["source_id"], unique=False)

    # 8. contradictions
    op.create_table(
        "contradictions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("finding_a_id", sa.UUID(), nullable=False),
        sa.Column("finding_b_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("resolution_status", sa.String(length=50), server_default="unresolved", nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["finding_a_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_b_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contradictions_finding_a_id"), "contradictions", ["finding_a_id"], unique=False)
    op.create_index(op.f("ix_contradictions_finding_b_id"), "contradictions", ["finding_b_id"], unique=False)
    op.create_index(op.f("ix_contradictions_research_run_id"), "contradictions", ["research_run_id"], unique=False)

    # 9. conclusions
    op.create_table(
        "conclusions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("research_run_id", sa.UUID(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conclusions_research_run_id"), "conclusions", ["research_run_id"], unique=False)

    # 10. conclusion_findings (Association table)
    op.create_table(
        "conclusion_findings",
        sa.Column("conclusion_id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["conclusion_id"], ["conclusions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conclusion_id", "finding_id"),
    )


def downgrade() -> None:
    op.drop_table("conclusion_findings")
    op.drop_index(op.f("ix_conclusions_research_run_id"), table_name="conclusions")
    op.drop_table("conclusions")
    op.drop_index(op.f("ix_contradictions_research_run_id"), table_name="contradictions")
    op.drop_index(op.f("ix_contradictions_finding_b_id"), table_name="contradictions")
    op.drop_index(op.f("ix_contradictions_finding_a_id"), table_name="contradictions")
    op.drop_table("contradictions")
    op.drop_index(op.f("ix_evidences_source_id"), table_name="evidences")
    op.drop_index(op.f("ix_evidences_source_content_id"), table_name="evidences")
    op.drop_index(op.f("ix_evidences_finding_id"), table_name="evidences")
    op.drop_table("evidences")
    op.drop_index(op.f("ix_findings_research_run_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_finding_type"), table_name="findings")
    op.drop_table("findings")
    op.drop_index(op.f("ix_source_contents_source_id"), table_name="source_contents")
    op.drop_table("source_contents")
    op.drop_index(op.f("ix_research_sources_research_run_id"), table_name="research_sources")
    op.drop_table("research_sources")
    op.drop_index(op.f("ix_research_runs_status"), table_name="research_runs")
    op.drop_index(op.f("ix_research_runs_question_id"), table_name="research_runs")
    op.drop_table("research_runs")
    op.drop_index(op.f("ix_research_questions_project_id"), table_name="research_questions")
    op.drop_table("research_questions")
    op.drop_index(op.f("ix_research_projects_status"), table_name="research_projects")
    op.drop_index(op.f("ix_research_projects_name"), table_name="research_projects")
    op.drop_table("research_projects")
