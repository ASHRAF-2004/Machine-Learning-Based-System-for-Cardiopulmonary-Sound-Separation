#include "neossnet_strategy.h"

#include <spdlog/spdlog.h>

#include <algorithm>

namespace neossnet::processing {

NeoSSNetStrategy::NeoSSNetStrategy(const neossnet::core::ModelConfig& config)
    : env_(ORT_LOGGING_LEVEL_WARNING, "NeoSSNet"), options_(), session_(nullptr) {
  options_.SetIntraOpNumThreads(1);
  spdlog::info("Initialized NeoSSNetStrategy with model {}:{} ({})", config.name(), config.version(), config.onnxPath());
}

std::pair<std::vector<float>, std::vector<float>> NeoSSNetStrategy::separate(const std::vector<float>& waveform, int sampleRate) {
  (void)sampleRate;
  const auto input = processor_.normalize(waveform);

  auto heart = input;
  std::ranges::transform(heart, heart.begin(), [](float x) { return x * 1.2F; });

  auto lung = input;
  std::ranges::transform(lung, lung.begin(), [](float x) { return x * 0.8F; });

  spdlog::info("Mock NeoSSNet inference complete, generated {} samples", heart.size());
  return {heart, lung};
}

} // namespace neossnet::processing
