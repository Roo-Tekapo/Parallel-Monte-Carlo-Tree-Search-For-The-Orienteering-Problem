cmake_minimum_required(VERSION 3.10)
project(OrienteeringMCTS)

set(CMAKE_CXX_STANDARD 17)

include_directories(include)

add_executable(main src/main.cpp src/MCTS.cpp src/Orienteering.cpp)

# Tests
enable_testing()
add_subdirectory(tests)
