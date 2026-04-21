#pragma once

#include "core/model_config.h"
#include "core/recording.h"
#include "core/separation_result.h"
#include "processing/pipeline_factory.h"
#include "processing/separation_strategy.h"
#include "services/notification_center.h"
#include "storage/result_repository.h"

#include <memory>
#include <stdexcept>

namespace neossnet::services {

class SeparationException : public std::runtime_error {
public:
  using std::runtime_error::runtime_error;
};

class SeparationService {
public:
  SeparationService(std::unique_ptr<neossnet::processing::PipelineFactory> factory,
                    std::unique_ptr<neossnet::storage::ResultRepository> repository,
                    std::unique_ptr<NotificationCenter> notifier,
                    neossnet::core::ModelConfig config);

  neossnet::core::SeparationResult processRecording(const neossnet::core::Recording& recording);

private:
  std::unique_ptr<neossnet::processing::PipelineFactory> factory_;
  std::unique_ptr<neossnet::storage::ResultRepository> repository_;
  std::unique_ptr<NotificationCenter> notifier_;
  neossnet::core::ModelConfig modelConfig_;
};

} // namespace neossnet::services
