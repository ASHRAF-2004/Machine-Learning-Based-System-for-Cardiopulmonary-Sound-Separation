cmake_minimum_required(VERSION 3.20)
project(neossnet_app VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(DEFINED ENV{VCPKG_ROOT} AND NOT DEFINED CMAKE_TOOLCHAIN_FILE)
  set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake" CACHE STRING "vcpkg toolchain")
endif()

find_package(Crow CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(unofficial-sqlite3 CONFIG REQUIRED)
find_package(sqlite_modern_cpp CONFIG REQUIRED)
find_package(SndFile CONFIG REQUIRED)
find_package(FFTW3 CONFIG REQUIRED)
find_package(onnxruntime CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)
find_package(GTest CONFIG REQUIRED)

add_library(neossnet_core
  src/core/recording.cpp
  src/core/separation_result.cpp
  src/core/model_config.cpp
  src/storage/sqlite_manager.cpp
  src/storage/result_repository.cpp
  src/processing/separation_strategy.cpp
  src/processing/neossnet_strategy.cpp
  src/processing/pipeline_factory.cpp
  src/processing/audio_processor.cpp
  src/services/notification_center.cpp
  src/services/separation_service.cpp
  src/api/upload_controller.cpp
  src/api/results_controller.cpp
)

target_include_directories(neossnet_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

target_link_libraries(neossnet_core PUBLIC
  Crow::Crow
  nlohmann_json::nlohmann_json
  unofficial::sqlite3::sqlite3
  sqlite_modern_cpp::sqlite_modern_cpp
  SndFile::sndfile
  FFTW3::fftw3f
  onnxruntime::onnxruntime
  spdlog::spdlog
)

add_executable(neossnet_app src/main.cpp)
target_link_libraries(neossnet_app PRIVATE neossnet_core)

enable_testing()
add_executable(neossnet_tests
  tests/test_notification_center.cpp
  tests/test_strategy_and_factory.cpp
  tests/test_service.cpp
)
target_link_libraries(neossnet_tests PRIVATE
  neossnet_core
  GTest::gtest_main
)
include(GoogleTest)
gtest_discover_tests(neossnet_tests)
