#include "model_config.h"

namespace neossnet::core {

ModelConfig::ModelConfig(std::string id, std::string name, std::string version, std::string onnxPath)
    : id_(std::move(id)), name_(std::move(name)), version_(std::move(version)), onnxPath_(std::move(onnxPath)) {}

const std::string& ModelConfig::id() const noexcept { return id_; }
const std::string& ModelConfig::name() const noexcept { return name_; }
const std::string& ModelConfig::version() const noexcept { return version_; }
const std::string& ModelConfig::onnxPath() const noexcept { return onnxPath_; }

} // namespace neossnet::core
