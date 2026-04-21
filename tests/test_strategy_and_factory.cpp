#include "core/model_config.h"
#include "processing/pipeline_factory.h"

#include <gtest/gtest.h>

TEST(StrategyFactoryTest, CreatesNeoSSNetStrategy) {
  neossnet::core::ModelConfig config("id", "NeoSSNet", "1.0", "models/neossnet.onnx");
  neossnet::processing::NeoSSNetFactory factory;

  auto strategy = factory.createStrategy(config);
  const auto [heart, lung] = strategy->separate({0.5F, -0.5F}, 4000);

  ASSERT_EQ(heart.size(), 2);
  ASSERT_EQ(lung.size(), 2);
  EXPECT_FLOAT_EQ(heart[0], 1.2F);
  EXPECT_FLOAT_EQ(lung[0], 0.8F);
}
