#pragma once

#include "core/model_config.h"
#include "processing/separation_strategy.h"

#include <memory>

namespace neossnet::processing {

class PipelineFactory {
public:
  virtual std::unique_ptr<SeparationStrategy> createStrategy(neossnet::core::ModelConfig& config) = 0;
  virtual ~PipelineFactory() = default;
};

class NeoSSNetFactory : public PipelineFactory {
public:
  std::unique_ptr<SeparationStrategy> createStrategy(neossnet::core::ModelConfig& config) override;
};

} // namespace neossnet::processing
