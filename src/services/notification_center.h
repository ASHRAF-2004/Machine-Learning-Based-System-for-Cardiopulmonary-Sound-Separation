#pragma once

#include <memory>
#include <string>
#include <vector>

namespace neossnet::services {

class ResultObserver {
public:
  virtual void onResultReady(const std::string& recordingId, const std::string& resultId) = 0;
  virtual ~ResultObserver() = default;
};

class UIObserver : public ResultObserver {
public:
  void onResultReady(const std::string& recordingId, const std::string& resultId) override;
};

class AuditObserver : public ResultObserver {
public:
  void onResultReady(const std::string& recordingId, const std::string& resultId) override;
};

class NotificationCenter {
public:
  void attach(std::unique_ptr<ResultObserver> observer);
  void notifyResultReady(const std::string& recordingId, const std::string& resultId);

private:
  std::vector<std::unique_ptr<ResultObserver>> observers_;
};

} // namespace neossnet::services
