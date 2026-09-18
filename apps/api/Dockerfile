FROM debian:bookworm-slim AS media-build
ARG FFMPEG_VERSION=7.1.1
ARG FFMPEG_SHA256=733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ca-certificates curl xz-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN curl -fsSLO https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz && echo "${FFMPEG_SHA256}  ffmpeg-${FFMPEG_VERSION}.tar.xz" | sha256sum -c - && tar -xf ffmpeg-${FFMPEG_VERSION}.tar.xz
WORKDIR /build/ffmpeg-7.1.1
# No GPL/nonfree codecs, no automatic linkage to external codecs. Native MPEG-4 encoder is sufficient.
RUN ./configure --prefix=/opt/ffmpeg --disable-gpl --disable-nonfree --disable-autodetect --disable-x86asm --disable-doc --disable-debug --disable-everything --enable-ffmpeg --enable-ffprobe --enable-protocol=file,pipe --enable-demuxer=mov,matroska --enable-decoder=h264,hevc,mpeg4,vp8,vp9,png,mjpeg --enable-parser=h264,hevc,mpeg4video,vp8,vp9 --enable-encoder=mpeg4 --enable-muxer=mp4,mov --enable-filter=color,testsrc2,format --enable-swscale --enable-avfilter && make -j2 && make install
RUN mkdir -p /opt/ffmpeg/share/licenses && cp COPYING.LGPLv2.1 /opt/ffmpeg/share/licenses/ && /opt/ffmpeg/bin/ffmpeg -L

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=media-build /opt/ffmpeg /opt/ffmpeg
ENV FFMPEG_PATH=/opt/ffmpeg/bin/ffmpeg FFPROBE_PATH=/opt/ffmpeg/bin/ffprobe
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
COPY alembic ./alembic
COPY alembic.ini ./
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
