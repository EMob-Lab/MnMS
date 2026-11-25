# syntax=docker/dockerfile:1

# A build context `wheel_dir` is expected to build this image.
# This build context must point to a directory containing the MnMS wheel file to install.
#
# For example, to build the image from the repository root:
#   python -m build --wheel
#   docker build -t <image-name> --build-context wheel_dir=dist docker/image_src
#
# Remark: the `dist` directory must not contain any wheel file from a previous build,
# as the build step fails if it finds more than one wheel file in it.
#
# When the image is built by the deployment workflow and published to the container registry,
# the metadata (title, description...) defined in labels.txt are attached to the image
# (they are not applied when the image is built with `docker build`, as in the example above).

FROM python:3.14-slim

# Environment variables:
# - PIP_NO_CACHE_DIR: don't keep pip's cache in the image
# - PIP_DISABLE_PIP_VERSION_CHECK: silence the warning issued if a newer pip is available online
# - PIP_ROOT_USER_ACTION: silence the warning about running pip as root
ENV \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# App installation
WORKDIR /app
RUN --mount=type=bind,from=wheel_dir,target=/context pip install /context/mnms-*.whl
COPY entrypoint.sh entrypoint-usage.txt /app

# Runtime configuration
WORKDIR /data
ENTRYPOINT ["/app/entrypoint.sh"]

# To be launched with:
#
# docker run -it --rm --volume "$PWD:/data" <image-name> <args...>
#
# ... or if the docker engine runs as root:
#
# docker run -it --rm --volume "$PWD:/data" --user "$(id -u):$(id -g)" --env HOME=/tmp <image-name> <args...>
#
# Use the launchers scripts to avoid typing this command line manually:
# - for MacOS/Linux: https://raw.githubusercontent.com/EMob-Lab/MnMS/refs/heads/main/docker/launchers/mnms-docker
# - for Windows: https://raw.githubusercontent.com/EMob-Lab/MnMS/refs/heads/main/docker/launchers/mnms-docker.cmd
