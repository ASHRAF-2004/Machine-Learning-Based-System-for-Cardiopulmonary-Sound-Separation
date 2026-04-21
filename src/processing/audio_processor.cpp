#include "audio_processor.h"

#include <algorithm>
#include <cmath>

namespace neossnet::processing {

std::vector<float> AudioProcessor::normalize(const std::vector<float>& input) const {
  if (input.empty()) {
    return {};
  }
  const auto maxIt = std::max_element(input.begin(), input.end(), [](float a, float b) { return std::abs(a) < std::abs(b); });
  const float maxMag = std::abs(*maxIt);
  if (maxMag <= 1e-8F) {
    return input;
  }

  std::vector<float> output = input;
  std::ranges::transform(output, output.begin(), [maxMag](float x) { return x / maxMag; });
  return output;
}

float AudioProcessor::estimateSdr(const std::vector<float>& mixed, const std::vector<float>& heart, const std::vector<float>& lung) const {
  const std::size_t n = std::min({mixed.size(), heart.size(), lung.size()});
  if (n == 0) {
    return 0.0F;
  }
  double signal = 0.0;
  double error = 0.0;
  for (std::size_t i = 0; i < n; ++i) {
    const float recon = heart[i] + lung[i];
    signal += static_cast<double>(mixed[i]) * mixed[i];
    const double e = static_cast<double>(mixed[i]) - recon;
    error += e * e;
  }
  if (error < 1e-9) {
    return 99.0F;
  }
  return static_cast<float>(10.0 * std::log10(signal / error));
}

} // namespace neossnet::processing
