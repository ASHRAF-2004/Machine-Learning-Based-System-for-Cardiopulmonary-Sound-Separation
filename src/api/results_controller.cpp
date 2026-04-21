#include "services/separation_service.h"
#include "storage/result_repository.h"

#include <crow.h>
#include <nlohmann/json.hpp>

namespace neossnet::api {

void registerResultRoutes(crow::SimpleApp& app,
                          neossnet::services::SeparationService& separationService,
                          neossnet::storage::ResultRepository& repository) {
  CROW_ROUTE(app, "/api/separate/<string>").methods(crow::HTTPMethod::Post)(
      [&separationService, &repository](const std::string& recordingId) {
        const auto rec = repository.findRecordingById(recordingId);
        if (!rec.has_value()) {
          return crow::response(404, "Recording not found");
        }
        const auto result = separationService.processRecording(rec.value());
        nlohmann::json payload = {{"resultId", result.id()}, {"heartPath", result.heartPath()}, {"lungPath", result.lungPath()}, {"sdr", result.sdr()}};
        return crow::response{payload.dump()};
      });

  CROW_ROUTE(app, "/results/<string>").methods(crow::HTTPMethod::Get)([&repository](const std::string& recordingId) {
    const auto result = repository.findResultByRecordingId(recordingId);
    if (!result.has_value()) {
      return crow::response(404, "Result not found");
    }

    nlohmann::json payload = {{"recordingId", recordingId},
                              {"resultId", result->id()},
                              {"heartDownload", "/" + result->heartPath()},
                              {"lungDownload", "/" + result->lungPath()},
                              {"sdr", result->sdr()}};
    return crow::response{payload.dump()};
  });
}

} // namespace neossnet::api
