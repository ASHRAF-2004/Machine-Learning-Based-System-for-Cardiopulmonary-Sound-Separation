#include "recording.h"

namespace neossnet::core {

Recording::Recording(std::string id, std::string filepath, int sampleRate, float durationSeconds)
    : id_(std::move(id)), filepath_(std::move(filepath)), sampleRate_(sampleRate), durationSeconds_(durationSeconds) {}

const std::string& Recording::id() const noexcept { return id_; }
const std::string& Recording::filepath() const noexcept { return filepath_; }
int Recording::sampleRate() const noexcept { return sampleRate_; }
float Recording::durationSeconds() const noexcept { return durationSeconds_; }

} // namespace neossnet::core
