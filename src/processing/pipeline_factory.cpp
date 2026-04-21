#include "pipeline_factory.h"

#include "processing/neossnet_strategy.h"

namespace neossnet::processing {

std::unique_ptr<SeparationStrategy> NeoSSNetFactory::createStrategy(neossnet::core::ModelConfig& config) {
  return std::make_unique<NeoSSNetStrategy>(config);
}

} // namespace neossnet::processing
