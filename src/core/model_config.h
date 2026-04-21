#pragma once

#include <string>

namespace neossnet::core {

class ModelConfig {
public:
  ModelConfig(std::string id, std::string name, std::string version, std::string onnxPath);

  [[nodiscard]] const std::string& id() const noexcept;
  [[nodiscard]] const std::string& name() const noexcept;
  [[nodiscard]] const std::string& version() const noexcept;
  [[nodiscard]] const std::string& onnxPath() const noexcept;

private:
  std::string id_;
  std::string name_;
  std::string version_;
  std::string onnxPath_;
};

} // namespace neossnet::core
