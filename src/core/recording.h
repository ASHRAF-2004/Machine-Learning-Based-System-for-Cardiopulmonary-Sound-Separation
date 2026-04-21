#pragma once

#include <string>

namespace neossnet::core {

class Recording {
public:
  Recording(std::string id, std::string filepath, int sampleRate, float durationSeconds);

  [[nodiscard]] const std::string& id() const noexcept;
  [[nodiscard]] const std::string& filepath() const noexcept;
  [[nodiscard]] int sampleRate() const noexcept;
  [[nodiscard]] float durationSeconds() const noexcept;

private:
  std::string id_;
  std::string filepath_;
  int sampleRate_{};
  float durationSeconds_{};
};

} // namespace neossnet::core
