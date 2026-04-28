"""SQLAlchemy models matching database/schema.sql."""

from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, Text, text
from sqlalchemy.orm import relationship

from app.database.db import Base


class UploadedAudio(Base):
    __tablename__ = "uploaded_audio"

    uploaded_audio_id = Column(Integer, primary_key=True)
    original_filename = Column(Text, nullable=False)
    stored_path = Column(Text, nullable=False, unique=True)
    file_hash = Column(Text, unique=True)
    mime_type = Column(Text, nullable=False, server_default=text("'audio/wav'"))
    sample_rate_hz = Column(Integer)
    channels = Column(Integer)
    bit_depth = Column(Integer)
    duration_sec = Column(Float)
    file_size_bytes = Column(Integer)
    uploaded_at = Column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    notes = Column(Text)

    jobs = relationship("SeparationJob", back_populates="uploaded_audio")


class Model(Base):
    __tablename__ = "model"

    model_id = Column(Integer, primary_key=True)
    model_name = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    architecture = Column(Text, nullable=False, server_default=text("'NeoSSNet'"))
    framework = Column(Text, nullable=False, server_default=text("'PyTorch'"))
    checkpoint_path = Column(Text, nullable=False, unique=True)
    config_path = Column(Text)
    description = Column(Text)
    is_active = Column(Integer, nullable=False, server_default=text("1"))
    created_at = Column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    jobs = relationship("SeparationJob", back_populates="model")


class SeparationJob(Base):
    __tablename__ = "separation_job"

    job_id = Column(Integer, primary_key=True)
    uploaded_audio_id = Column(
        Integer,
        ForeignKey("uploaded_audio.uploaded_audio_id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_id = Column(
        Integer,
        ForeignKey("model.model_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(Text, nullable=False)
    requested_at = Column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    started_at = Column(Text)
    completed_at = Column(Text)
    processing_time_ms = Column(Integer)
    parameters_json = Column(Text)
    error_message = Column(Text)

    uploaded_audio = relationship("UploadedAudio", back_populates="jobs")
    model = relationship("Model", back_populates="jobs")
    result = relationship("SeparationResult", back_populates="job", uselist=False)
    logs = relationship("SystemLog", back_populates="job")


class SeparationResult(Base):
    __tablename__ = "separation_result"

    result_id = Column(Integer, primary_key=True)
    job_id = Column(
        Integer,
        ForeignKey("separation_job.job_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    heart_file_path = Column(Text, nullable=False, unique=True)
    lung_file_path = Column(Text, nullable=False, unique=True)
    output_sample_rate_hz = Column(Integer)
    output_duration_sec = Column(Float)
    heart_file_size_bytes = Column(Integer)
    lung_file_size_bytes = Column(Integer)
    created_at = Column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    job = relationship("SeparationJob", back_populates="result")
    metrics = relationship("EvaluationMetric", back_populates="result")


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metric"

    metric_id = Column(Integer, primary_key=True)
    result_id = Column(
        Integer,
        ForeignKey("separation_result.result_id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_name = Column(Text, nullable=False)
    metric_scope = Column(Text, nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(Text)
    reference_type = Column(Text)
    recorded_at = Column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    result = relationship("SeparationResult", back_populates="metrics")


class SystemLog(Base):
    __tablename__ = "system_log"

    log_id = Column(Integer, primary_key=True)
    job_id = Column(
        Integer,
        ForeignKey("separation_job.job_id", ondelete="CASCADE"),
    )
    log_level = Column(Text, nullable=False)
    source_component = Column(Text, nullable=False)
    event_type = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    job = relationship("SeparationJob", back_populates="logs")
