#pragma once

#include <utility>
#include <vector>

namespace neossnet::processing {

class SeparationStrategy {
public:
  virtual std::pair<std::vector<float>, std::vector<float>> separate(const std::vector<float>& waveform, int sampleRate) = 0;
  virtual ~SeparationStrategy() = default;
};

} // namespace neossnet::processing
