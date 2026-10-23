# Polski Piper dla Home Assistant: liczby, godziny, daty i jednostki czytane poprawnie

Obraz Dockera z syntezą mowy **Piper** (oficjalny `rhasspy/wyoming-piper` 2.5.2), do którego
dodano **polską normalizację tekstu** (`pl_tts`) i analizator morfologiczny **Morfeusz 2**.
Zanim tekst trafi do syntezy, każdy zapis, którego Piper nie umie przeczytać po polsku,
jest zamieniany na słowa, z poprawną odmianą:

| Tekst | Oryginalny Piper czyta | Ten Piper czyta |
|---|---|---|
| `o 9:05` | „o dziewięć zero pięć” | „o dziewiątej pięć” |
| `10:00-10:30` | „dziesięć zero zero…” | „od dziesiątej do dziesiątej trzydzieści” |
| `20.10.2026` | „dwadzieścia dziesięć dwa tysiące…” | „dwudziestego października dwa tysiące dwudziestego szóstego roku” |
| `-3,5°C` | „trzy przecinek pięć…” (gubi minus) | „minus trzy i pół stopnia Celsjusza” |
| `6°C` | „sześć stopień ce” | „sześć stopni Celsjusza” |
| `50 km/h` | „…ka em slesz ha” | „pięćdziesiąt kilometrów na godzinę” |
| `2 kWh`, `72 kg` | „…ka wu ha”, „…ka gie” | „dwie kilowatogodziny”, „siedemdziesiąt dwa kilogramy” |
| `Masz 1 otwartą roletę i 2 nowe wiadomości` | „jeden otwartą…”, „dwa nowe…” | „jedną otwartą roletę i dwie nowe wiadomości” |
| `z 2 osobami`, `brakuje 2 osób` | „z dwa osobami”, „brakuje dwa osób” | „z dwiema osobami”, „brakuje dwóch osób” |
| `ul. Kwiatowa 30/2` | „ul…” | „ulica Kwiatowa trzydzieści łamane przez dwa” |

Działa z **każdym polskim głosem** Pipera, również z samodzielnie wytrenowanym, i z każdym
źródłem tekstu: odpowiedziami Assista, `tts.speak`, automatyzacjami, skryptami i modelami LLM.

Repozytorium jest tylko po polsku, bo rozwiązuje problem specyficzny dla języka polskiego.

## Spis treści

- [Dlaczego to powstało](#dlaczego-to-powstało)
- [Jak do tego doszliśmy](#jak-do-tego-doszliśmy)
- [Co robi ta wersja, a czego nie robi oryginał](#co-robi-ta-wersja-a-czego-nie-robi-oryginał)
- [Czego nie robi](#czego-nie-robi)
- [Instalacja](#instalacja)
- [Konfiguracja](#konfiguracja)
- [Jak to działa w środku](#jak-to-działa-w-środku)
- [Rozwój i testy](#rozwój-i-testy)
- [Trenujesz własny głos?](#trenujesz-własny-głos)
- [Licencje](#licencje)

## Dlaczego to powstało

Piper nie czyta tekstu bezpośrednio. Najpierw program **espeak-ng** zamienia tekst na głoski
(fonemy), a dopiero te trafiają do modelu głosu:

```
tekst ──▶ espeak-ng (tekst → głoski) ──▶ model głosu (głoski → dźwięk)
```

Polski espeak-ng nie zna polskich zapisów godzin, dat i jednostek. `9:05` to dla niego „dziewięć
zero pięć”, `°C` to „stopień ce”, `km/h` to „ka em slesz ha”, a minus przed liczbą dziesiętną
znika. Nie pilnuje też odmiany: liczebnik nie zgadza się z rzeczownikiem („dwa osoby”).

Model głosu dostaje już złe głoski i wymawia je wiernie. **Dlatego nowy trening głosu tego nie
naprawi**: nawet idealnie wytrenowany głos powie dokładnie to, co dostał od espeak-ng. Poprawić
trzeba tekst, zanim zobaczy go espeak-ng. Wtedy poprawka działa dla każdego głosu.

W Home Assistant takich zapisów jest bardzo dużo: godziny spotkań z kalendarza, temperatury,
zużycie energii, zasięg samochodu, stany baterii, daty. Asystent głosowy, który czyta „sześć
stopień ce”, brzmi źle, nawet jeśli sam głos jest bardzo dobry.

## Jak do tego doszliśmy

Projekt powstał w październiku 2026 przy asystencie głosowym działającym na co dzień w domu
(Home Assistant, satelity głosowe, Piper na NVIDIA Jetson AGX Orin 64 GB, na procesorze).

### Punkt wyjścia: stary obraz i podejrzenie wobec głosu

Piper działał na obrazie `dustynv/wyoming-piper` z 2024 roku, z własnym głosem wytrenowanym
od zera. Godziny, daty i jednostki brzmiały źle. Pierwsze podejrzenie: błędy w przygotowaniu
danych do treningu głosu, więc może trzeba trenować od nowa?

### Krok 1: aktualizacja Pipera

Przejście na oficjalny `rhasspy/wyoming-piper:2.5.2` (nowy Piper z `OHF-Voice/piper1-gpl`)
dało:
- mowę zdanie po zdaniu w trybie strumieniowym (dłuższa odpowiedź zaczyna się szybciej);
- pauzę między zdaniami (`--sentence-silence`);
- panel WWW do wgrywania głosów;
- fonemy w `[[ ]]` do poprawiania wymowy pojedynczych słów.

Czytanie liczb zostało jednak takie samo.

### Krok 2: diagnoza

Test samego espeak-ng pokazał, że błędy powstają **przed** modelem głosu (tabela na górze). Głos
był w porządku, więc ponowny trening odpadł.

### Krok 3: czym poprawiać tekst

Rozważyliśmy trzy drogi:

| Droga | Za | Przeciw |
|---|---|---|
| Model AI do normalizacji (`Folx/qwen3-0.6b-pl-text-normalization`) | rozumie dowolny zapis | według autora ok. 8–9% błędów, nie pilnuje odmiany („pięć procent” zamiast „pięciu procent”), wymaga GPU, osobnego kontenera i tokenu Hugging Face |
| Duży model językowy (np. Bielik) | bardzo dobra odmiana | sekundy na każde zdanie, zbyt wolno do czytania każdego komunikatu |
| **Reguły w Pythonie + słownik morfologiczny** | przewidywalne (ten sam tekst = ten sam wynik), ułamek milisekundy, bez GPU, każdy błąd poprawia się jedną regułą i testem | trzeba napisać reguły dla każdego formatu |

Wybór: reguły, **wbudowane bezpośrednio w kontener Pipera**, żeby nie rozrzucać rozwiązania po
osobnych usługach. Każdy tekst, który trafia do Pipera, jest poprawiany, bez względu na to,
skąd przyszedł.

### Wersja 1: reguły dla godzin, dat i jednostek

Godziny z odmianą po przyimku („o dziewiątej”, „do dwudziestej pierwszej”), przedziały godzin,
daty, lata, jednostki, liczby ujemne i dziesiętne, skróty (`ul.`, `np.`, `itd.`). 134 testy.

Problem: z rzeczownikiem zgadzały się tylko jednostki ze słownika („dwie kilowatogodziny”).
Przy zwykłych rzeczownikach wychodziło „jeden osoba”, „dwa osoby”, „dwa dzieci”.

### Wersja 1.1: słownik rodzajów

Słownik rodzajów (ok. 7,9 tys. form) zbudowany z Morfeusza 2 offline i dołączony jako plik
JSON: „jedna osoba”, „dwie lampy”, „dwoje dzieci”, „dwóch mężczyzn”. 190 testów. Działało
jednak tylko dla słów, które były w słowniku.

### Wersja 2: reguły z prawdziwych danych Home Assistant

Narzędzie `tools/ha_audit.py` buduje zdania, jakie HA może wypowiedzieć dla każdej encji
(„nazwa: stan jednostka”), przepuszcza je przez normalizację i wypisuje, gdzie zostały cyfry
albo symbole. Pierwszy przebieg: 2108 encji, 907 stanów z wartościami, 46 problemów w 13
wzorcach. Z tego powstały nowe reguły:
- zaokrąglanie długich ułamków z liczników (`3027.18552 kWh` → „trzy tysiące dwadzieścia siedem
  kilowatogodzin”);
- kwoty (`11132.14 PLN` → „jedenaście tysięcy sto trzydzieści dwa złote czternaście groszy”);
- czas UTC ze stanów HA przeliczany na czas polski (z czasem letnim);
- kody pocztowe, numery domów („łamane przez”), wersje i adresy IP („kropka”);
- czasy trwania (`Pozostało 1:23:45`, minutniki);
- identyfikatory zostają bez zmian (`CR2450`, `CO2`, adresy MAC, UUID);
- jednostki spotykane w HA (BMI, UVI, dB/m, var, kvarh, kB/s…).

Słownik rozszerzony o przypadki (ok. 65 tys. form, 1,8 MB): „z dwiema osobami”, „o trzech
kamerach”, „bez pięciu osób”. 300 testów.

### Wersja 2.1: Morfeusz 2 w kontenerze

Zamiast słownika w pliku: **Morfeusz 2** (IPI PAN, C++, słownik SGJP) wbudowany w obraz
i pytany na żywo o każde słowo po liczbie. Działa z **dowolnym** polskim rzeczownikiem, bez
listy słów, w ok. 0,1–0,2 ms na zdanie. Gotowych pakietów Morfeusza dla arm64 nie ma, więc
obraz kompiluje go ze źródeł. 316 testów.

### Wersja 3: pozostałe zapisy i wymowa

- przypadek wymuszony czasownikiem lub przeczeniem: „brakuje 2 osób” → „dwóch osób”, „nie ma 5
  lamp” → „pięciu lamp”;
- jednostki w przypadkach zależnych: „do 5 km” → „do pięciu kilometrów”, „po 3 min” → „po
  trzech minutach”;
- przedziały czytane jak na głos: „2-3 osoby” → „dwie, trzy osoby”;
- godziny z kropką i „godz.”: „w godz. 17.30-18.00” → „w godzinach od siedemnastej trzydzieści
  do osiemnastej”;
- liczebniki porządkowe: „na 2. piętrze” → „na drugim piętrze”, „w XXI wieku”, „Jan Paweł II”;
- wyniki („2:1” → „dwa do jednego”), ułamki („2/3” → „dwie trzecie”);
- telefony, e-maile („małpa”, „kropka”), adresy WWW, emotikony (pomijane);
- wymowa obcych słów i nazw (`pl_tts/pronunciations.py`): „iPhone” → „ajfon”, „review” →
  „riwju”, „Home Assistant” → „Hołm Asystent”.

**378 testów.** Ta wersja działa na co dzień w domu autora.

## Co robi ta wersja, a czego nie robi oryginał

| | Oryginalny `wyoming-piper` 2.5.2 | Ten obraz |
|---|---|---|
| Godziny („o 9:05”, „10:00-10:30”, „godz. 17.30”) | czyta cyfry | słowa, z odmianą po przyimku |
| Daty, lata, czas z HA (ISO, UTC) | czyta cyfry | „dwudziestego października…”, czas polski |
| Jednostki (°C, %, km/h, kWh, kg, hPa…) | literuje symbole | pełne nazwy, w dobrej liczbie i przypadku |
| Liczby ujemne i dziesiętne | gubi minus, „przecinek” | „minus trzy i pół” |
| Zgodność liczebnika z rzeczownikiem | brak | rodzaj i przypadek z Morfeusza 2, dla każdego rzeczownika |
| Skróty (ul., np., itd., ok., godz., tel.) | czyta jak słowa albo literuje | rozwija |
| Kwoty, ułamki, wyniki, kody pocztowe, numery domów | cyfry i symbole | słowa |
| Telefony, e-maile, adresy WWW, emotikony | literuje albo czyta symbole | czytelne słowa, emotikony pomijane |
| Obce słowa i nazwy | polskie reguły dla angielskich słów | słownik wymowy, łatwy do rozszerzenia |
| Dziennik zmian tekstu | brak | `normalize: 'oryginał' -> 'tekst czytany'` |

Wszystko inne działa jak w oryginale: te same argumenty, głosy, strumieniowanie, panel głosów,
protokół Wyoming. Normalizację można wyłączyć zmienną `PL_TTS_NORMALIZE=0` bez przebudowy.

## Czego nie robi

- **Nie zmienia głosu ani modelu.** Brzmienie, tempo i akcent zależą od głosu; tu zmienia się
  tylko tekst.
- **Nie używa AI.** To reguły i słownik morfologiczny: tekst, którego reguły nie znają, przechodzi
  bez zmian.
- **Nie poprawia gramatyki** całych zdań, tylko zapisy liczb, dat, jednostek i skrótów.
- **Tylko język polski.** Normalizacja działa na każdym tekście, który dostaje Piper, bez względu
  na wybrany głos. Jeśli ten sam serwer czyta też głosem w innym języku, wyłącz normalizację
  (`PL_TTS_NORMALIZE=0`) albo uruchom dla niego osobny kontener.
- **Znane ograniczenia:**
  - po przyimkach, które łączą się i z biernikiem, i z miejscownikiem („o”, „w”, „na”), jednostka
    zostaje w bierniku („o 5 stopni”);
  - przypadek wymuszony czasownikiem działa tylko dla czasowników i zwrotów z listy w
    `normalize.py` (`_GEN_PREPS`, `_GEN_PHRASES`);
  - formy naprawdę niejednoznaczne (np. „wnuczki” od „wnuczka” i „wnuczek”) dostają zwykły
    liczebnik;
  - skróty pisane wielkimi literami (np. „PR”, „AGD”) espeak literuje, chyba że są w słowniku
    wymowy.
- **Nie przyspiesza syntezy.** Normalizacja dodaje ułamek milisekundy; czas mowy zależy od
  głosu i sprzętu.

## Instalacja

Wymagania: Docker z Compose, procesor amd64 albo arm64 (np. Raspberry Pi 4/5, mini PC, NVIDIA
Jetson). GPU nie jest potrzebne: głosy „medium” są na procesorze szybkie.

1. Pobierz repozytorium obok swojego `docker-compose.yaml`:

   ```sh
   git clone https://github.com/witold-gren/home-assistant-polish-piper
   ```

2. Dodaj (albo podmień) usługę `piper`:

   ```yaml
   services:
     piper:
       build: ./home-assistant-polish-piper
       image: local/polish-piper:2.5.2
       container_name: piper
       restart: unless-stopped
       ports:
         - "10200:10200"          # Wyoming - adres dla Home Assistant
         - "10205:5000"           # opcjonalnie: panel WWW do głosów
       volumes:
         - ./piper/models:/data   # głosy: *.onnx + *.onnx.json
         - /etc/localtime:/etc/localtime:ro
       command:
         - --voice=pl_PL-gosia-medium     # albo Twój własny głos z ./piper/models
         - --length-scale=1.0             # tempo (większe = wolniej)
         - --sentence-silence=0.25        # pauza między zdaniami (s)
         - --update-voices
         # panel głosów (bez logowania - tylko w sieci domowej):
         # - --web-server
         # - --web-server-host=0.0.0.0
         # - --web-server-allow=192.168.1.0/24
       # environment:
       #   PL_TTS_NORMALIZE: "0"          # wyłącza normalizację bez przebudowy
   ```

   Gotowy plik: [docker-compose.example.yaml](docker-compose.example.yaml).

3. Zbuduj i uruchom. Pierwsze budowanie trwa kilka minut, bo kompiluje Morfeusza; kolejne
   kilkanaście sekund:

   ```sh
   docker compose build piper
   docker compose up -d piper
   docker logs -f piper
   ```

   Przy budowaniu obraz sam sprawdza, czy Morfeusz działa, i zamienia przykładowe zdanie.

4. W Home Assistant: Ustawienia → Urządzenia i usługi → Dodaj integrację → **Wyoming
   Protocol**, host komputera z kontenerem, port `10200`. Jeśli integracja już była, wystarczy
   ją przeładować.

5. Test: Narzędzia deweloperskie → Akcje → `tts.speak` z tekstem
   `Jutro o 17:30, na zewnątrz -3,5°C, wiatr 12 km/h, masz 2 nowe wiadomości.`. Podgląd zamiany:

   ```sh
   docker logs piper | grep normalize
   ```

Powrót do oryginału: w `docker-compose.yaml` zamień `build:` na
`image: rhasspy/wyoming-piper:2.5.2` i usuń `image: local/polish-piper:2.5.2`. Głosy zostają w tym
samym katalogu.

### Wersje

Numer wersji tego repozytorium to **wersja `wyoming-piper` w obrazie**: `v2.5.2` to
`rhasspy/wyoming-piper:2.5.2` (silnik `piper-tts` 1.8.0) z normalizacją. Dzięki temu łatwo
przepiąć się między oryginałem a tą wersją i od razu widać, na którym Piperze działa obraz.
Poprawki samej normalizacji na tym samym Piperze dostają dopisek: `v2.5.2-2`, `v2.5.2-3`…
Konkretne wydanie: `git -C home-assistant-polish-piper checkout v2.5.2`, potem
`docker compose build piper`.

## Konfiguracja

| Co | Gdzie |
|---|---|
| Argumenty Pipera (głos, tempo, pauzy, panel) | `command:`, jak w oryginalnym `wyoming-piper` |
| Wyłączenie normalizacji | `PL_TTS_NORMALIZE=0` w `environment:` |
| Wymowa obcych słów i nazw | `pl_tts/pronunciations.py`: słowo → zapis „po polsku”, potem przebudowa obrazu |
| Nowe jednostki i skróty | `UNITS` i `ABBREVIATIONS` w `pl_tts/normalize.py` |
| Nowsza wersja słownika Morfeusza | `MORFEUSZ_VERSION` w `Dockerfile` (lista: download.sgjp.pl/morfeusz/) |

## Jak to działa w środku

- **`pl_tts/run.py`** uruchamia serwer `wyoming-piper` tak jak oryginał i podmienia dwie metody
  obsługi zdarzeń:
  - cały tekst zwykłej syntezy jest normalizowany, **zanim** Piper podzieli go na zdania (inaczej
    „ul.” albo „20.10.2026” zostałyby rozcięte na kropkach);
  - w trybie strumieniowym normalizowane jest każde zdanie osobno. Normalizacja jest
    idempotentna, więc drugi przebieg niczego nie zmienia.
- **`pl_tts/normalize.py`** stosuje reguły w ustalonej kolejności: emotikony, e-maile i adresy
  WWW, telefony, słownik wymowy, separatory tysięcy, daty ISO, ochrona identyfikatorów, kody
  pocztowe, ułamki, godziny i przedziały, czasy trwania, daty, lata, liczebniki porządkowe,
  liczby rzymskie, przedziały liczb, ilości z jednostkami, liczby ujemne, dziesiętne i
  pozostałe liczby.
- **`pl_tts/numbers.py`** zamienia liczby na słowa: główne, porządkowe, zbiorowe („dwoje”,
  „pięciorgiem”), w każdym przypadku i rodzaju.
- **`pl_tts/morph.py`** pyta Morfeusza 2 o słowo po liczbie (rodzaj, liczba, przypadek) i
  zapamiętuje wyniki. Bez Morfeusza normalizacja nadal działa, ale liczebniki zostają w
  mianowniku.
- **Bezpieczeństwo:** błąd w regule nigdy nie zabiera mowy, bo Piper dostaje wtedy tekst
  oryginalny, a błąd trafia do dziennika.

## Rozwój i testy

Testy (378 przypadków: tekst → oczekiwane słowa) uruchamia się w obrazie, bo tam jest Morfeusz:

```sh
docker compose build piper
docker run --rm --entrypoint bash \
  -v "$PWD/home-assistant-polish-piper/tests:/usr/src/tests:ro" local/polish-piper:2.5.2 \
  -c "cd /usr/src && .venv/bin/pip3 install -q pytest && .venv/bin/python3 -m pytest -q tests"
```

Poprawka błędu:
1. Znajdź zdanie, które brzmi źle (`docker logs piper | grep normalize`).
2. Dopisz przypadek do `tests/test_normalize.py`.
3. Popraw regułę w `pl_tts/normalize.py`, uruchom testy, przebuduj obraz.

**Audyt na danych z Twojego Home Assistant:** `tools/ha_audit.py` czyta stany wszystkich encji
(REST API, token długoterminowy) i pokazuje, gdzie po normalizacji zostały cyfry albo symbole:

```sh
docker run --rm --entrypoint bash -v "$PWD/home-assistant-polish-piper:/w:ro" -v "$HOME/hass_token:/token:ro" \
  local/polish-piper:2.5.2 -c "cd /w && /usr/src/.venv/bin/python3 tools/ha_audit.py \
  --api http://192.168.1.10:8123 --token-file /token"
```

Zgłoszenia zdań, które brzmią źle, i propozycje reguł: Issues w repozytorium. Najlepiej z
tekstem wejściowym i tym, jak powinien zabrzmieć.

## Trenujesz własny głos?

Normalizacja naprawia tekst przed syntezą, ale dane treningowe też mają znaczenie:
- transkrypcje w `metadata.csv` bez cyfr, symboli i skrótów: dokładnie to, co słychać
  w nagraniu;
- nagrania WAV 22 050 Hz, mono, 16 bit (nie MP3);
- dużo zdań z liczbami, godzinami i jednostkami wypowiedzianymi słownie;
- kontrola transkrypcji przez `espeak-ng -v pl --ipa` i Whisper;
- start z gotowego polskiego modelu (np. `pl_PL-gosia-medium`) zamiast od zera.

## Licencje

- Kod w tym repozytorium (`pl_tts`, testy, narzędzia, Dockerfile): [Apache-2.0](LICENSE).
- Obraz bazowy: [wyoming-piper](https://github.com/OHF-Voice/wyoming-piper) (MIT) i
  [Piper](https://github.com/OHF-Voice/piper1-gpl) (GPL-3.0). Budując obraz, korzystasz z nich
  na ich licencjach.
- [Morfeusz 2](http://morfeusz.sgjp.pl/) (IPI PAN) ze słownikiem SGJP, pobierany i kompilowany
  przy budowaniu obrazu: [licencja](http://morfeusz.sgjp.pl/doc/license).
- Głosy Pipera mają własne licencje, opisane przy każdym głosie.
