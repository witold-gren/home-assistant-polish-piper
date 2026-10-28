# Wyoming Piper 2.5.2 (piper1-gpl) + Polish text normalization (pl_tts) with
# the Morfeusz 2 morphological analyser (IPI PAN, SGJP dictionary).
# Numbers, times, dates, units and abbreviations are turned into words before
# the text reaches espeak-ng; numerals agree with the noun they describe.

ARG PIPER_IMAGE=rhasspy/wyoming-piper:2.5.2
ARG MORFEUSZ_VERSION=20261018

# --- stage 1: build Morfeusz (there are no ready packages for arm64) --------
FROM ${PIPER_IMAGE} AS morfeusz
ARG MORFEUSZ_VERSION
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential cmake swig python3-dev curl ca-certificates
WORKDIR /build
RUN curl -fsSL -O http://download.sgjp.pl/morfeusz/${MORFEUSZ_VERSION}/morfeusz-src-${MORFEUSZ_VERSION}.tar.gz \
 && curl -fsSL -O http://download.sgjp.pl/morfeusz/${MORFEUSZ_VERSION}/morfeusz2-dictionary-sgjp-${MORFEUSZ_VERSION}.tgz \
 && tar xzf morfeusz-src-${MORFEUSZ_VERSION}.tar.gz \
 && mkdir -p /out/dict && tar xzf morfeusz2-dictionary-sgjp-${MORFEUSZ_VERSION}.tgz -C /out/dict
# Without the Java and GUI wrappers and without tests (they need JDK, Qt, cppunit);
# setup.cfg forces an x86_64 wheel tag - drop it so the wheel matches this architecture
RUN sed -i 's/^add_subdirectory (java)/#add_subdirectory (java)/' Morfeusz/morfeusz/wrappers/CMakeLists.txt \
 && sed -i 's/^add_subdirectory (gui)/#&/; s/^add_subdirectory (fsabuilder)/#&/' Morfeusz/CMakeLists.txt \
 && mkdir b && cd b \
 && cmake ../Morfeusz -DCMAKE_BUILD_TYPE=Release -DSKIP_TESTING=1 -DSKIP_DICTIONARY_BUILDING=1 \
      -DDEFAULT_DICT_NAME=sgjp -DDICT_VERSION=${MORFEUSZ_VERSION} \
      -DDEFAULT_DICT_DIR=/usr/share/morfeusz2/dictionaries -DCMAKE_INSTALL_PREFIX=/usr -DPY=3.0 \
 && make -j"$(nproc)" libmorfeusz py3morfeusz \
 && cp morfeusz/libmorfeusz2.so /out/ \
 && cd morfeusz/wrappers/python3 \
 && sed -i '/^plat_name/d; /^py_limited_api/d' setup.cfg \
 && /usr/src/.venv/bin/pip3 install -q setuptools wheel \
 && /usr/src/.venv/bin/pip3 wheel -q --no-build-isolation --no-deps -w /out/wheels .

# --- stage 2: Piper + Morfeusz + pl_tts --------------------------------------
FROM ${PIPER_IMAGE}
COPY --from=morfeusz /out/libmorfeusz2.so /usr/lib/
COPY --from=morfeusz /out/dict/ /usr/share/morfeusz2/dictionaries/
COPY --from=morfeusz /out/wheels/ /tmp/wheels/
RUN ldconfig && /usr/src/.venv/bin/pip3 install -q --no-deps /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY pl_tts/ /usr/src/pl_tts/

# Build-time check: Morfeusz works, PyYAML is there (own pronunciations) and a sample text is normalized
RUN cd /usr/src && .venv/bin/python3 -c "import yaml; from pl_tts import normalize, morph; assert morph.AVAILABLE; print(normalize('O 9:05 jest -3,5°C, masz 1 otwartą roletę i 2 nowe wiadomości, zapytaj Jarvisa.'))"

# Like docker_run.sh of the base image, but through pl_tts.run.
# PL_TTS_NORMALIZE=0 turns normalization off without rebuilding; own pronunciations
# are read from /data/pronunciations.yaml (PL_TTS_PRONUNCIATIONS changes the path).
ENTRYPOINT ["bash", "-c", "cd /usr/src && exec .venv/bin/python3 -m pl_tts.run --uri tcp://0.0.0.0:10200 --data-dir /data \"$@\"", "--"]
