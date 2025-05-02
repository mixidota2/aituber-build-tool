FROM ubuntu:latest

WORKDIR /work

# install uv
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates wget
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

COPY ./src /work/src
COPY ./uv.lock /work/uv.lock
COPY ./pyproject.toml /work/pyproject.toml

RUN uv sync

# setup voicevox library
RUN curl -sSfL https://github.com/VOICEVOX/voicevox_core/releases/latest/download/download-linux-x64 -o download
RUN chmod +x download
RUN printf "q\ny\n" | ./download --exclude c-api
# setup voicevox_core
RUN wget https://github.com/VOICEVOX/voicevox_core/releases/download/0.16.0/voicevox_core-0.16.0-cp310-abi3-manylinux_2_34_x86_64.whl
RUN uv add voicevox_core-0.16.0-cp310-abi3-manylinux_2_34_x86_64.whl

#CMD ["uv", "run", "python", "-m", "src.main"]
