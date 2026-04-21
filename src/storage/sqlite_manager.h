#pragma once

#include <memory>
#include <sqlite_modern_cpp.h>
#include <string>

namespace neossnet::storage {

class SQLiteManager {
public:
  explicit SQLiteManager(std::string dbPath);
  void initializeSchema();
  [[nodiscard]] sqlite::database& connection() noexcept;

private:
  std::string dbPath_;
  std::unique_ptr<sqlite::database> db_;
};

} // namespace neossnet::storage
