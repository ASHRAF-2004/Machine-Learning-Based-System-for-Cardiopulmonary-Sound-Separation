#include "separation_result.h"

namespace neossnet::core {

SeparationResult::SeparationResult(std::string id, std::string recordingId, std::string heartPath, std::string lungPath, float sdr)
    : id_(std::move(id)),
      recordingId_(std::move(recordingId)),
      heartPath_(std::move(heartPath)),
      lungPath_(std::move(lungPath)),
      sdr_(sdr) {}

const std::string& SeparationResult::id() const noexcept { return id_; }
const std::string& SeparationResult::recordingId() const noexcept { return recordingId_; }
const std::string& SeparationResult::heartPath() const noexcept { return heartPath_; }
const std::string& SeparationResult::lungPath() const noexcept { return lungPath_; }
float SeparationResult::sdr() const noexcept { return sdr_; }

} // namespace neossnet::core
