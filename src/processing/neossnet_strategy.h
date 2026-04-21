#pragma once

#include "core/model_config.h"
#include "processing/audio_processor.h"
#include "processing/separation_strategy.h"

#include <onnxruntime_cxx_api.h>

namespace neossnet::processing {

class NeoSSNetStrategy : public SeparationStrategy {
public:
  explicit NeoSSNetStrategy(const neossnet::core::ModelConfig& config);
  std::pair<std::vector<float>, std::vector<float>> separate(const std::vector<float>& waveform, int sampleRate) override;

private:
  Ort::Env env_;
  Ort::SessionOptions options_;
  Ort::Session* session_;
  AudioProcessor processor_;
};

} // namespace neossnet::processing
