#include "core/recording.h"
#include "storage/result_repository.h"

#include <crow.h>
#include <nlohmann/json.hpp>
#include <sndfile.hh>

#include <filesystem>
#include <fstream>
#include <random>

namespace neossnet::api {

namespace {
std::string generateId() {
  static constexpr char kChars[] = "0123456789abcdef";
  std::random_device rd;
  std::mt19937 gen(rd());
  std::uniform_int_distribution<> dist(0, 15);
  std::string out(16, '0');
  for (char& c : out) {
    c = kChars[dist(gen)];
  }
  return out;
}
} // namespace

void registerUploadRoutes(crow::SimpleApp& app, neossnet::storage::ResultRepository& repository) {
  CROW_ROUTE(app, "/api/upload").methods(crow::HTTPMethod::Post)([&repository](const crow::request& req) {
    const auto recordingId = generateId();
    std::filesystem::create_directories("public");
    const std::string filepath = "public/" + recordingId + ".wav";

    std::ofstream out(filepath, std::ios::binary);
    out.write(req.body.data(), static_cast<std::streamsize>(req.body.size()));

    SndfileHandle handle(filepath);
    const int sampleRate = handle.samplerate();
    const float duration = sampleRate > 0 ? static_cast<float>(handle.frames()) / static_cast<float>(sampleRate) : 0.0F;

    neossnet::core::Recording recording(recordingId, filepath, sampleRate, duration);
    repository.saveRecording(recording);

    nlohmann::json payload = {{"recordingId", recordingId}, {"sampleRate", sampleRate}, {"duration", duration}};
    return crow::response{payload.dump()};
  });
}

} // namespace neossnet::api
