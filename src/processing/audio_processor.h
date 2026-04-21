#pragma once

#include <vector>

namespace neossnet::processing {

class AudioProcessor {
public:
  [[nodiscard]] std::vector<float> normalize(const std::vector<float>& input) const;
  [[nodiscard]] float estimateSdr(const std::vector<float>& mixed, const std::vector<float>& heart, const std::vector<float>& lung) const;
};

} // namespace neossnet::processing
