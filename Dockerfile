# Wyoming Piper 2.5.2 (piper1-gpl) + polska normalizacja tekstu (pl_tts) z
# analizatorem morfologicznym Morfeusz 2 (IPI PAN, słownik SGJP).
# Liczby, godziny, daty, jednostki i skróty są zamieniane na słowa, zanim
# tekst trafi do espeak-ng; liczebniki odmieniają się zgodnie z rzeczownikiem.

ARG PIPER_IMAGE=rhasspy/wyoming-piper:2.5.2
ARG MORFEUSZ_VERSION=20261018

# --- etap 1: kompilacja Morfeusza (nie ma gotowych pakietów dla arm64) ------
FROM ${PIPER_IMAGE} AS morfeusz
ARG MORFEUSZ_VERSION
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential cmake swig python3-dev curl ca-certificates
WORKDIR /build
RUN curl -fsSL -O http://download.sgjp.pl/morfeusz/${MORFEUSZ_VERSION}/morfeusz-src-${MORFEUSZ_VERSION}.tar.gz \
 && curl -fsSL -O http://download.sgjp.pl/morfeusz/${MORFEUSZ_VERSION}/morfeusz2-dictionary-sgjp-${MORFEUSZ_VERSION}.tgz \
 && tar xzf morfeusz-src-${MORFEUSZ_VERSION}.tar.gz \
 && mkdir -p /out/dict && tar xzf morfeusz2-dictionary-sgjp-${MORFEUSZ_VERSION}.tgz -C /out/dict
# Bez nakładek Java i GUI oraz bez testów (wymagają JDK, Qt, cppunit);
# setup.cfg wymusza tag koła x86_64 - usuwamy go, żeby powstało koło dla tej architektury
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

# --- etap 2: Piper + Morfeusz + pl_tts ---------------------------------------
FROM ${PIPER_IMAGE}
COPY --from=morfeusz /out/libmorfeusz2.so /usr/lib/
COPY --from=morfeusz /out/dict/ /usr/share/morfeusz2/dictionaries/
COPY --from=morfeusz /out/wheels/ /tmp/wheels/
RUN ldconfig && /usr/src/.venv/bin/pip3 install -q --no-deps /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY pl_tts/ /usr/src/pl_tts/

# Kontrola przy budowaniu: Morfeusz działa, przykładowy tekst jest zamieniany
RUN cd /usr/src && .venv/bin/python3 -c "from pl_tts import normalize, morph; assert morph.AVAILABLE; print(normalize('O 9:05 jest -3,5°C, masz 1 otwartą roletę i 2 nowe wiadomości.'))"

# Jak docker_run.sh z obrazu bazowego, ale przez pl_tts.run.
# PL_TTS_NORMALIZE=0 wyłącza normalizację bez przebudowy.
ENTRYPOINT ["bash", "-c", "cd /usr/src && exec .venv/bin/python3 -m pl_tts.run --uri tcp://0.0.0.0:10200 --data-dir /data \"$@\"", "--"]
