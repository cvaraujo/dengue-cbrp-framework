FROM --platform=linux/amd64 ubuntu as ubuntu-build-base
RUN apt update -y; \
    apt upgrade -y; \
    apt install -y build-essential libboost-all-dev python3; \
    apt clean -y

FROM --platform=linux/amd64 ubuntu-build-base as ubuntu-cmake
# Install CMake
# Specify CMake version
ARG CMAKE_VERSION=3.24.2
RUN  apt install -y wget; \
    wget https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-x86_64.sh -O cmake.sh; \
    sh cmake.sh --prefix=/usr/local/ --exclude-subdir; \
    rm -rf cmake.sh;

RUN wget https://packages.gurobi.com/11.0/gurobi11.0.3_linux64.tar.gz \
    tar -xvf gurobi.tar.gz;
    
RUN wget http://lemon.cs.elte.hu/pub/sources/lemon-1.3.1.tar.gz \
    tar -xvf lemon.tar.gz;

RUN wget https://archives.boost.io/release/1.86.0/source/boost_1_86_0.tar.gz \
    tar -xvf boost.tar.gz;

FROM --platform=linux/amd64 ubuntu-cmake as ubuntu-builder
