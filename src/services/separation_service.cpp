#include "separation_service.h"

#include "processing/audio_processor.h"

#include <sndfile.hh>
#include <spdlog/spdlog.h>

#include <filesystem>
#include <random>

namespace neossnet::services {

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

SeparationService::SeparationService(std::unique_ptr<neossnet::processing::PipelineFactory> factory,
                                     std::unique_ptr<neossnet::storage::ResultRepository> repository,
                                     std::unique_ptr<NotificationCenter> notifier,
                                     neossnet::core::ModelConfig config)
    : factory_(std::move(factory)), repository_(std::move(repository)), notifier_(std::move(notifier)), modelConfig_(std::move(config)) {}

neossnet::core::SeparationResult SeparationService::processRecording(const neossnet::core::Recording& recording) {
  SndfileHandle inFile(recording.filepath());
  if (inFile.error() != 0) {
    throw SeparationException("Unable to open recording file");
  }

  std::vector<float> mixed(static_cast<std::size_t>(inFile.frames() * inFile.channels()));
  const auto read = inFile.readf(mixed.data(), inFile.frames());
  mixed.resize(static_cast<std::size_t>(read * inFile.channels()));

  auto strategy = factory_->createStrategy(modelConfig_);
  const auto [heart, lung] = strategy->separate(mixed, recording.sampleRate());

  std::filesystem::create_directories("public");
  const std::string resultId = generateId();
  const std::string heartPath = "public/heart_" + resultId + ".wav";
  const std::string lungPath = "public/lung_" + resultId + ".wav";

  SndfileHandle heartOut(heartPath, SFM_WRITE, inFile.format(), 1, recording.sampleRate());
  SndfileHandle lungOut(lungPath, SFM_WRITE, inFile.format(), 1, recording.sampleRate());
  heartOut.writef(heart.data(), static_cast<sf_count_t>(heart.size()));
  lungOut.writef(lung.data(), static_cast<sf_count_t>(lung.size()));

  const neossnet::processing::AudioProcessor processor;
  const float sdr = processor.estimateSdr(mixed, heart, lung);

  neossnet::core::SeparationResult result(resultId, recording.id(), heartPath, lungPath, sdr);
  repository_->saveResult(result);
  notifier_->notifyResultReady(recording.id(), result.id());

  spdlog::info("Processed recording {} into result {}", recording.id(), result.id());
  return result;
}

} // namespace neossnet::services
