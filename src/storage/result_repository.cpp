#include "result_repository.h"

namespace neossnet::storage {

ResultRepository::ResultRepository(SQLiteManager& sqliteManager) : sqliteManager_(sqliteManager) {}

void ResultRepository::saveRecording(const neossnet::core::Recording& recording) {
  sqliteManager_.connection() << "INSERT INTO recordings (id, filepath, sample_rate, duration) VALUES (?, ?, ?, ?);" << recording.id()
                              << recording.filepath() << recording.sampleRate() << recording.durationSeconds();
}

void ResultRepository::saveResult(const neossnet::core::SeparationResult& result) {
  sqliteManager_.connection() << "INSERT INTO results (id, recording_id, heart_path, lung_path, sdr) VALUES (?, ?, ?, ?, ?);" << result.id()
                              << result.recordingId() << result.heartPath() << result.lungPath() << result.sdr();
}

std::optional<neossnet::core::Recording> ResultRepository::findRecordingById(const std::string& id) {
  std::optional<neossnet::core::Recording> maybe;
  sqliteManager_.connection() << "SELECT id, filepath, sample_rate, duration FROM recordings WHERE id = ?;" << id >>
      [&](std::string rid, std::string path, int rate, float duration) { maybe.emplace(std::move(rid), std::move(path), rate, duration); };
  return maybe;
}

std::optional<neossnet::core::SeparationResult> ResultRepository::findResultByRecordingId(const std::string& recordingId) {
  std::optional<neossnet::core::SeparationResult> maybe;
  sqliteManager_.connection() << "SELECT id, recording_id, heart_path, lung_path, sdr FROM results WHERE recording_id = ?;" << recordingId >>
      [&](std::string id, std::string recId, std::string heart, std::string lung, float sdr) {
        maybe.emplace(std::move(id), std::move(recId), std::move(heart), std::move(lung), sdr);
      };
  return maybe;
}

} // namespace neossnet::storage
