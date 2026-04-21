#include "processing/audio_processor.h"

#include <gtest/gtest.h>

TEST(AudioProcessorTest, NormalizeKeepsRange) {
  neossnet::processing::AudioProcessor processor;
  auto out = processor.normalize({2.0F, -1.0F, 0.5F});

  ASSERT_EQ(out.size(), 3);
  EXPECT_FLOAT_EQ(out[0], 1.0F);
  EXPECT_FLOAT_EQ(out[1], -0.5F);
}
