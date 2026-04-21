#pragma once

#include <string>

namespace neossnet::core {

class SeparationResult {
public:
  SeparationResult(std::string id, std::string recordingId, std::string heartPath, std::string lungPath, float sdr);

  [[nodiscard]] const std::string& id() const noexcept;
  [[nodiscard]] const std::string& recordingId() const noexcept;
  [[nodiscard]] const std::string& heartPath() const noexcept;
  [[nodiscard]] const std::string& lungPath() const noexcept;
  [[nodiscard]] float sdr() const noexcept;

private:
  std::string id_;
  std::string recordingId_;
  std::string heartPath_;
  std::string lungPath_;
  float sdr_{};
};

} // namespace neossnet::core
