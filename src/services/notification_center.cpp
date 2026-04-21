#include "notification_center.h"

#include <spdlog/spdlog.h>

namespace neossnet::services {

void UIObserver::onResultReady(const std::string& recordingId, const std::string& resultId) {
  spdlog::info("UIObserver: recording {} produced result {}", recordingId, resultId);
}

void AuditObserver::onResultReady(const std::string& recordingId, const std::string& resultId) {
  spdlog::info("AuditObserver: event REC={} RES={}", recordingId, resultId);
}

void NotificationCenter::attach(std::unique_ptr<ResultObserver> observer) { observers_.push_back(std::move(observer)); }

void NotificationCenter::notifyResultReady(const std::string& recordingId, const std::string& resultId) {
  for (const auto& observer : observers_) {
    observer->onResultReady(recordingId, resultId);
  }
}

} // namespace neossnet::services
