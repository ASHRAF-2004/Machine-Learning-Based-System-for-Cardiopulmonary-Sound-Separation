#pragma once

#include "core/recording.h"
#include "core/separation_result.h"
#include "storage/sqlite_manager.h"

#include <optional>
#include <string>

namespace neossnet::storage {

class ResultRepository {
public:
  explicit ResultRepository(SQLiteManager& sqliteManager);

  void saveRecording(const neossnet::core::Recording& recording);
  void saveResult(const neossnet::core::SeparationResult& result);
  [[nodiscard]] std::optional<neossnet::core::Recording> findRecordingById(const std::string& id);
  [[nodiscard]] std::optional<neossnet::core::SeparationResult> findResultByRecordingId(const std::string& recordingId);

private:
  SQLiteManager& sqliteManager_;
};

} // namespace neossnet::storage
