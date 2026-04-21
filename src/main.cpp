#include "core/model_config.h"
#include "services/notification_center.h"
#include "services/separation_service.h"
#include "storage/result_repository.h"
#include "storage/sqlite_manager.h"

#include <crow.h>
#include <spdlog/spdlog.h>

#include <memory>

namespace neossnet::api {
void registerUploadRoutes(crow::SimpleApp& app, neossnet::storage::ResultRepository& repository);
void registerResultRoutes(crow::SimpleApp& app,
                          neossnet::services::SeparationService& separationService,
                          neossnet::storage::ResultRepository& repository);
} // namespace neossnet::api

int main() {
  crow::SimpleApp app;

  neossnet::storage::SQLiteManager sqliteManager("neossnet.db");
  sqliteManager.initializeSchema();

  auto repository = std::make_unique<neossnet::storage::ResultRepository>(sqliteManager);
  auto notifier = std::make_unique<neossnet::services::NotificationCenter>();
  notifier->attach(std::make_unique<neossnet::services::UIObserver>());
  notifier->attach(std::make_unique<neossnet::services::AuditObserver>());

  neossnet::core::ModelConfig modelConfig("model-default", "NeoSSNet", "1.0", "models/neossnet.onnx");

  auto separationService = std::make_unique<neossnet::services::SeparationService>(
      std::make_unique<neossnet::processing::NeoSSNetFactory>(),
      std::make_unique<neossnet::storage::ResultRepository>(sqliteManager),
      std::move(notifier),
      modelConfig);

  neossnet::api::registerUploadRoutes(app, *repository);
  neossnet::api::registerResultRoutes(app, *separationService, *repository);

  CROW_ROUTE(app, "/")([] { return crow::mustache::load("upload.html").render(); });
  CROW_ROUTE(app, "/results")([] { return crow::mustache::load("results.html").render(); });

  app.loglevel(crow::LogLevel::Info);
  spdlog::info("Starting NeoSSNet app on http://localhost:8080");
  app.port(8080).multithreaded().run();
}
