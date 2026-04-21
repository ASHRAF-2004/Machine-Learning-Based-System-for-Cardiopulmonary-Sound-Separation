#include "services/notification_center.h"

#include <gtest/gtest.h>

namespace {

class StubObserver final : public neossnet::services::ResultObserver {
public:
  void onResultReady(const std::string& recordingId, const std::string& resultId) override {
    lastRecording = recordingId;
    lastResult = resultId;
  }

  std::string lastRecording;
  std::string lastResult;
};

TEST(NotificationCenterTest, NotifiesAttachedObserver) {
  neossnet::services::NotificationCenter center;
  auto observer = std::make_unique<StubObserver>();
  auto* raw = observer.get();

  center.attach(std::move(observer));
  center.notifyResultReady("rec-1", "res-1");

  EXPECT_EQ(raw->lastRecording, "rec-1");
  EXPECT_EQ(raw->lastResult, "res-1");
}

} // namespace
