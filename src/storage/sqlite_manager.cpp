#include "sqlite_manager.h"

namespace neossnet::storage {

SQLiteManager::SQLiteManager(std::string dbPath) : dbPath_(std::move(dbPath)), db_(std::make_unique<sqlite::database>(dbPath_)) {}

void SQLiteManager::initializeSchema() {
  *db_ << "CREATE TABLE IF NOT EXISTS recordings (id TEXT PRIMARY KEY, filepath TEXT, sample_rate INT, duration FLOAT);";
  *db_ << "CREATE TABLE IF NOT EXISTS results (id TEXT PRIMARY KEY, recording_id TEXT, heart_path TEXT, lung_path TEXT, sdr FLOAT);";
  *db_ << "CREATE TABLE IF NOT EXISTS model_configs (id TEXT PRIMARY KEY, name TEXT, version TEXT, onnx_path TEXT);";
}

sqlite::database& SQLiteManager::connection() noexcept { return *db_; }

} // namespace neossnet::storage
