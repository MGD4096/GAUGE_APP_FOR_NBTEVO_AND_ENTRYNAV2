NBTEVO
![NBTEvo with running app](/images/20261121_185721.jpg)
EntryNav2
![EntryNav2 with running app](/images/20261121_181430.jpg)



# IDRIVE GAUGE APP – ekran silnika w stylu iDrive 7

Natywna aplikacja iDrive dla **NBT Evo** (ID5/ID6, QNX) i **EntryNav2** (EntryEVO, Linux). Jeden ekran w układzie
2-1-2:

- po lewej **temperatura płynu chłodniczego** i **oleju**,
- w środku **przeciążenie** (kropka na tarczy do 2 g, wartość całkowita, boczna i wzdłużna) i **bieg** (P R N D, przy
  D aktualny bieg skrzyni: D1, D2…),
- po prawej **moc** (KM) i **moment obrotowy** (Nm).

Przy płynie, oleju, mocy i momencie jest **maksimum bieżącego przejazdu** (żółty znacznik na łuku i liczba „max”).
Maksima liczą się od zera przy każdym starcie aplikacji; te z ostatniego przejazdu zostają w `max.txt`. Skala mocy
i momentu rośnie razem z maksimum.

**Limit ok. 60 obrazków w jednym stanie** (sprawdzone w aucie: obrazki od ok. 60. w górę zostają puste). Dlatego tylko
duże wartości są składane z cyfr (3 elementy), a pozostałe liczby (maksima, końce skal, paliwo, przeciążenie) są
gotowymi obrazkami całych liczb – jeden element na liczbę. Ekran ma 47 obrazków.
Obok biegów jest **ilość paliwa** w zbiorniku (`sensors.fuel`, `tanklevel`).

**Język** dopasowuje się do języka iDrive. Teksty menu i ustawień są w bazie tekstów (`pl.txt` po polsku, pozostałe
języki po angielsku), którą iDrive wybiera sam. Napisy na samym ekranie (tytuły kart, „bok/wzdł.”, „KM”, przecinek
dziesiętny) są w obrazkach, więc aplikacja wybiera je według `vehicle.language` z CDS: 18 = polski, każdy inny język
= angielski („Coolant”, „lat./long.”, „PS”, kropka dziesiętna). Dopóki język nie przyjdzie, ekran jest po polsku.
Podgląd angielski: [`res/preview_en.png`](res/preview_en.png).

**Ustawienia** (klawisz OPTION na ekranie GAUGE APP → Ustawienia; zapis w `<folder danych>/settings.txt`):
kolor wskaźników (niebieski, czerwony, pomarańczowy BMW, zielony), temperatura (°C / °F), moc (KM / kW / hp),
moment (Nm / lb-ft), paliwo (litry / galony US). Wartości i maksima są trzymane w jednostkach bazowych, przeliczane
jest tylko to, co widać. Klatki w kolorze wskaźników (łuki, kropka przeciążenia, podświetlony bieg) są w osobnej
paczce dla każdego koloru (`GaugeApp_frames_c0..3.bin`); aplikacja wczytuje tylko wybraną.

Wygląd z przykładowymi wartościami (wygenerowany przez `make_db.py`): [`res/preview.png`](res/preview.png).

Aplikacja pojawia się jako wiersz **GAUGE APP** w menu **ConnectedDrive** (`applicationType="OnlineServices"`,
sprawdzone na EntryNav2; samo `"Online"` nie działa). `python3 make_db.py --menu media` przenosi ją do menu Media/Radio (`applicationType="Custom"`, po
wierszu Bluetooth audio, tam gdzie NbtAad i entry-aad umieszczają „Android Auto”). Identyfikatory różnią się od
nich, więc obie aplikacje mogą być zainstalowane razem.

**Biegi:** w D auto wysyła w `driving.gear` bieg skrzyni + 4 (sprawdzone na EntryNav2 F40: 5 = D1). 4 to samo „D”.

## Jak to działa

HmiMain3D przy starcie ładuje `Plugins/GaugeApp/GaugeApp.manifest` (framework `PluginApp`, ten sam co w BMW
SecurityMenu / ActiveSeating, NbtAad i entry-aad). iDrive nie pozwala aplikacji rysować, więc cały ekran składa się
z obrazków:

- `GaugeApp.xml` opisuje obrazek tła (karty, podpisy, skale, tarcza) i 55 obrazków nad nim. Każdy z nich ma swoją
  pozycję w pikselach i model `raImageModel`, czyli obrazek, który aplikacja wysyła jako dane PNG.
- `GaugeApp_frames.bin` zawiera wszystkie klatki: łuki (61 kroków), znaczniki maksimum, cyfry w dwóch rozmiarach,
  kropkę przeciążenia (siatka 21×21, co 0,2 g) i pola biegów. Baza obrazków iDrive (`GaugeApp_ALL_Images.zip`) ma
  tylko ikonę wiersza menu.
- `libGaugeApp.so`:
  1. przy starcie wczytuje `GaugeApp_frames.bin`;
  2. po ok. 1,5 s subskrybuje właściwości **CDS** (Car Data Service) tym samym wywołaniem, którym NbtAad i entry-aad
     czytają `driving.gear`;
  3. co 200 ms wybiera klatkę dla każdego obrazka (`src/gauge_view.hpp`) i przez
     `PluginApp::updateModel(model, bmw::Image)` wysyła **tylko te, które się zmieniły**;
  4. wartość niedostępna, błędna albo nierealna (np. `{"error":400}`) pokazuje `--`.

Dlaczego tak, a nie przez bazę obrazków iDrive – diagnostyka na EntryNav2 (F40) pokazała, że:
- z 635 klatkami w bazie iDrive nie pokazuje **żadnego** obrazka (i zgłasza `onError 9`), a z kilkoma – wszystkie;
- obrazki wysyłane przez aplikację jako dane działają, zachowują pozycję x/y, nakładają się i można je wymieniać ok. 5
  razy na sekundę;
- widoczny obszar ekranu aplikacji to ok. 1250 × 470 px. Układ 960×400 jest skalowany ×1,15 do 1104×460 i
  wyśrodkowany (`SCALE`, `ORIGIN` w `make_db.py`).

| Właściwość CDS | Przykładowa wartość | Na ekranie |
|---|---|---|
| `engine.temperature` | `{"temperature":{"engine":19,"oil":18}}` | Płyn (50–130 °C), olej (50–150 °C) |
| `engine.torque` | `{"torque":380}` (Nm) | Moment |
| `engine.RPMSpeed` | `{"RPMSpeed":3600}` | tylko do mocy: KM = Nm × obr/min / 7023,5 |
| `driving.acceleration` | `{"acceleration":{"lateral":-0.19,"longitudinal":65535.00}}` | Przeciążenie (m/s² ÷ 9,81) |
| `driving.speedActual` | `{"speedActual":87}` | przeciążenie wzdłużne, gdy auto nie podaje `longitudinal` |
| `driving.gear` | `{"gear":6}` | Bieg (1 N, 2 R, 3 P, 4+ D1…) |

Nazwy i formaty: <https://bimmergestalt.github.io/BMWConnectedAnalysis/cds/> (lista społeczności; część jednostek
jest tam oznaczona jako „prawdopodobnie”). W CDS nie ma mocy silnika, dlatego jest liczona z momentu i obrotów.

**Maksima** zerują się przy każdym starcie aplikacji. Maksima ostatniego przejazdu są w `<folder danych>/max.txt`
(NBT Evo: `/var/opt/gaugeapp`, EntryNav2: `/var/local/data/GaugeApp`), np. `coolant=98.0`, zapisywane najwyżej co 30 s
i przy zamknięciu aplikacji, przez plik tymczasowy i zmianę nazwy. Nowe maksimum musi przyjść w **dwóch odczytach
z rzędu** (liczy się mniejszy z nich), więc pojedynczy błędny odczyt nie zostaje rekordem.

**Skala mocy i momentu:** od 0 do maksimum + 5 %, zaokrąglonego w górę do 50. Najmniejszy koniec skali to 150 KM i
250 Nm. Skala tylko rośnie.

## Co jest sprawdzone, a co nie

**Sprawdzone (na komputerze):**
- Logika: parsowanie, moc, przeciążenie z prędkości, maksima z ochroną przed pojedynczym błędnym odczytem,
  zapis i odczyt `max.txt`, wybór każdej klatki (`tests/test_cds_values.cpp`).
- Cały cykl życia aplikacji na atrapie frameworka, w obu wersjach: `pluginAppInfo`, `onInit`, subskrypcja 6
  właściwości, przełączanie tylko zmienionych obrazków, błędne dane, zapis maksimów w `onFinalize` i ich odczyt przy
  kolejnym `onInit` (`tests/app_host_test.cpp`). `make check`.
- Wszystkie funkcje `bmw::…`, których biblioteka używa, są eksportowane przez biblioteki EntryNav2 z auta (`nm -D`
  na `lib/Entry_Evo_libs`, identycznych z plikami zgranymi z jednostki), w tym `Image(unsigned char const*, unsigned)`
  i `updateModel(unsigned, Image const&)`. Budowa obiektu `bmw::Image` (28 bajtów: nazwa pliku i bufor) jest odczytana
  z kodu maszynowego `libCoreFramework`.
- Wersja EntryNav2 kompiluje się na ARM (hard-float, NEON) i wymaga tylko `GLIBC_2.4`.

**Sprawdzone w aucie (EntryNav2, F40):** ładowanie aplikacji, wiersz w menu, stany i przejścia, etykiety, obrazki
wysyłane jako dane z pozycjami i nakładaniem, odświeżanie ok. 5 klatek/s, dane CDS: `engine.temperature`,
`engine.RPMSpeed`, `engine.torque`, `driving.gear`, `driving.acceleration` (z osią wzdłużną; 65535 tylko w pierwszym
odczycie), `driving.speedActual`; zapis maksimów.

**Niesprawdzone – do potwierdzenia w aucie:**
- **Cały docelowy ekran** (56 obrazków wysyłanych jako dane) – poszczególne elementy działają w diagnostyce, całość
  jeszcze nie była uruchomiona.
- **Wersja NBT Evo:** kompilacja `qcc` (nie ma tu QNX SDP 6.5) i to, czy budowa `bmw::Image` jest taka sama jak na
  EntryNav2.
- **Znak przyspieszenia** (`kLatSign`, `kLonSign` w `src/cds_values.hpp`) i znaczenie `engine.temperature.engine`
  (porównaj z zegarem). Surowe wartości trafiają do logu.

> Ingerencja w head unit odbywa się na Twoją odpowiedzialność. Aplikacja niczego nie patchuje i zapisuje tylko we
> własnym folderze danych.

## Wymagania

- **NBT Evo:** dostęp root/SSH i jedno z kodowań **A4A, A4A_REMOTE_APPS, REMOTE_HMI, TOUCH_COMMAND** (bez tego
  HmiMain3D nie ładuje PluginApps), jak w NbtAad.
- **EntryNav2:** dostęp root przez SSH (kabel ENET), jak w entry-aad.

## Budowanie

Wygenerowane pliki (`GaugeApp.xml`, `src/gauge_ids.hpp`, oba zipy, `res/preview.png`) są w repozytorium, więc do samej
kompilacji Pillow nie jest potrzebny. Po zmianie wyglądu:

```
python3 make_db.py              # Pillow + font DejaVu Sans (--font plik.ttf, --x / --y: przesunięcie ekranu)
make check                      # testy hostowe obu wersji (zwykły g++)
```

**NBT Evo:** QNX SDP 6.5.0 (`qcc`; instaluje się razem z QNX Momentics IDE 4.7) i kopie bibliotek BMW z
`/opt/hmi/ID5/lib` w `lib/NBT_evo_libs`.

- **Windows:** `build_nbt.bat` (albo `build_nbt.bat D:\QNX650`, jeśli QNX nie jest w `C:\QNX650`). Skrypt sam wywoła
  `qnx650-env.bat`, skompiluje bibliotekę i złoży w `dist\nbt\GaugeApp` wszystko, co trzeba skopiować na jednostkę.
- **Linux / obraz qnx650-docker:** `make` (`libGaugeApp.so`).
- **Momentics IDE** (jeśli wolisz projekt): *File → New → QNX C/C++ Project*, typ *Shared Library*, wariant
  **armle-v7** (so), biblioteka C++ **GNU libstdc++** (nie Dinkum – tak jak HmiMain3D); źródło `src/engine_data.cpp`,
  ścieżka nagłówków `src`, definicja `_QNX_SOURCE`, do linkowania `libAppFramework.A.so` i `libCoreFramework.A.so`
  z `lib/NBT_evo_libs` oraz opcja linkera `--allow-shlib-undefined`; nazwa wyniku `libGaugeApp.so`.

Kod jest w C++98 (GCC 4.4.2 z SDP 6.5); na komputerze kompiluje się `g++ -std=gnu++98` bez ostrzeżeń, ale `qcc`
nie był tu uruchomiony. Wszystkie funkcje BMW, których używa, są w bibliotekach z `lib/NBT_evo_libs` (`nm -D`),
a obiekt `bmw::Image` ma na NBT tę samą budowę co na EntryNav2 (sprawdzone w kodzie maszynowym).

**EntryNav2:** kopie `libAppFramework.A.so` i `libCoreFramework.A.so` z `/opt/hmi/lib` w `lib/Entry_Evo_libs` i
obraz Dockera z `toolchain/Dockerfile` (Ubuntu 12.04: armhf GCC 4.6 i eglibc 2.15, ta sama wersja co w aucie).
Nowszy kompilator podlinkowałby funkcje, których auto nie ma (np. `clock_gettime@GLIBC_2.17`).

```
docker build -t gauge-entrynav2-tc toolchain        # raz
bash toolchain/tc-entrynav2.sh make entrynav2-dist  # Windows: docker run --rm -v "%CD%:/work" -w /work gauge-entrynav2-tc make entrynav2-dist
```

Wynik: `dist/gauge-app-entrynav2.tar` (biblioteka, manifest, XML, dwa zipy, `MD5SUMS`).

## Instalacja

### NBT Evo

Pełna instrukcja krok po kroku: [NbtEvo_Installation.md](NbtEvo_Installation.md). W skrócie – na head unit, pliki
z pendrive'a (`/fs/usb0` albo `/mnt/umass…`):

```
mkdir -p /opt/hmi/ID5/data/ro/Plugins/GaugeApp
cp /mnt/umassXXXX/libGaugeApp.so /mnt/umassXXXX/GaugeApp.manifest /mnt/umassXXXX/GaugeApp.xml \
   /mnt/umassXXXX/GaugeApp_ALL_Texts.zip /mnt/umassXXXX/GaugeApp_ALL_Images.zip /opt/hmi/ID5/data/ro/Plugins/GaugeApp/
```

Jeśli kopiowanie kończy się „read-only file system”, przemontuj cel do zapisu tak samo, jak przy NbtAad. Potem
przytrzymaj przycisk zasilania ok. 30 s (restart).

### EntryNav2

Przez SSH, kablem ENET, tak jak entry-aad (auto stoi, zapłon włączony, nie wyłączać w trakcie zapisu):

```
scp dist/gauge-app-entrynav2.tar root@169.254.1.0:/tmp/
ssh root@169.254.1.0
cd /tmp && mkdir -p gauge && tar -xf gauge-app-entrynav2.tar -C gauge && cd gauge && md5sum -c MD5SUMS
LD_TRACE_LOADED_OBJECTS=1 LD_WARN=yes LD_BIND_NOW=yes LD_LIBRARY_PATH=/usr/local/lib:/opt/hmi/lib:/usr/lib:/lib \
    /lib/ld-linux-armhf.so.3 ./opt/hmi/data/ro/Plugins/GaugeApp/libGaugeApp.so 2>&1 | grep -E 'not found|undefined symbol'
mount -o remount,rw /
mkdir -p /opt/hmi/data/ro/Plugins/GaugeApp
rm -f /opt/hmi/data/ro/Plugins/GaugeApp/*
cp opt/hmi/data/ro/Plugins/GaugeApp/* /opt/hmi/data/ro/Plugins/GaugeApp/
chmod 755 /opt/hmi/data/ro/Plugins/GaugeApp/libGaugeApp.so
sync
mount -o remount,ro /
cd / && md5sum -c /tmp/gauge/MD5SUMS && rm -rf /tmp/gauge /tmp/gauge-app-entrynav2.tar
reboot
```

- Polecenie z `LD_TRACE_LOADED_OBJECTS` nie może nic wypisać (każda linia = brakująca biblioteka lub funkcja).
- `/var/local/data` jest zamontowany z `noexec`, dlatego biblioteka musi leżeć na partycji systemowej.
- `rm -f` przed kopiowaniem: iDrive trzyma starą bibliotekę w pamięci do restartu.

W **ConnectedDrive** powinien pojawić się wiersz **GAUGE APP**.

### Obie wersje

| | NBT Evo | EntryNav2 |
|---|---|---|
| Folder aplikacji | `/opt/hmi/ID5/data/ro/Plugins/GaugeApp` | `/opt/hmi/data/ro/Plugins/GaugeApp` |
| Folder danych (maksima, wyłącznik) | `/var/opt/gaugeapp` | `/var/local/data/GaugeApp` |
| Log | `slog` (`sloginfo \| grep GaugeApp`) + pendrive | `gauge-app.log` w folderze danych (512 KB) + pendrive |
| Ochrona przed pętlą restartów | brak | 3 restarty HMI w < 2 min po załadowaniu → aplikacja się wyłącza |

- **Wyłączenie bez usuwania:** `touch <folder danych>/app.disable` i restart.
- **Po zadziałaniu ochrony (EntryNav2):** sprawdź log, potem `rm -f /var/local/data/GaugeApp/app-guard` i restart.
- **Odinstalowanie:** usuń folder aplikacji (i folder danych, jeśli maksima nie są potrzebne), restart.
- **Aktualizacja:** jak instalacja; `max.txt` zostaje.

## Diagnostyka

**Log na pendrivie:** utwórz na komputerze pusty plik `gauge-app.log` na pendrivie i włóż go do auta – log będzie
dopisywany tam (limit 4 MB). NBT Evo szuka go w `/mnt/umass*`, EntryNav2 w każdym folderze pod `/media`, `/mnt` i
`/run/media`.

Każda właściwość CDS trafia do logu w surowej postaci przy pierwszych 5 odczytach, np.
`CDS driving.acceleration = '{"acceleration":{"lateral":-0.19,"longitudinal":65535.00}}' -> ok`. Z tego widać, co
Twoje auto naprawdę wysyła i czy jednostki się zgadzają.

**Brak danych (wszędzie `--`):** 25 s po starcie w logu pojawi się `no CDS value arrived…`. Auto nie publikuje tych
właściwości aplikacjom albo subskrypcja się nie powiodła – prześlij fragment logu.

**Ekran się rozsypał** (obrazki jeden pod drugim, ucięte, przesunięte): iDrive inaczej traktuje pozycje obrazków.
Prześlij zdjęcie ekranu; pozycję całości można przesunąć `make_db.py --x/--y`, a układ zmienić w `make_db.py`.

**Brak wiersza w menu:** sprawdź kodowanie (NBT Evo), obecność wszystkich 5 plików, konflikt `entryButtonFocusID` /
`<id>` w manifeście oraz log HMI.

## Dostosowanie

- **Wygląd, układ, kolory, napisy, zakresy płynu i oleju, najmniejsze końce skal:** stałe na górze `make_db.py`,
  potem `python3 make_db.py` i przebudowa.
- **Jednostka / znak przyspieszenia, przelicznik mocy:** stałe „tuning” w `src/cds_values.hpp`.
- **Częstotliwość odświeżania i zapisu maksimów:** `kRenderMs`, `kSaveEveryS` w `src/engine_data.cpp`.

## Układ projektu

```
make_db.py                 układ ekranu -> GaugeApp.xml, src/gauge_ids.hpp, oba zipy, res/preview.png
src/cds_values.hpp         parsowanie CDS, moc, przeciążenie, maksima (czysta logika, testowana)
src/gauge_view.hpp         która klatka w którym obrazku (czysta logika, testowana)
src/gauge_ids.hpp          wygenerowane: identyfikatory obrazków i slotów
src/engine_data.cpp        aplikacja: PluginApp, subskrypcja CDS, przełączanie obrazków, max.txt (obie wersje)
GaugeApp.xml               wygenerowane: wiersz menu + ekran z obrazkami
GaugeApp.manifest          manifest dla CAppManager
toolchain/                 obraz Dockera i skrypt do budowy wersji EntryNav2
tests/                     testy hostowe i atrapa frameworka (obie wersje)
lib/NBT_evo_libs, lib/Entry_Evo_libs   kopie bibliotek BMW z aut (nie są częścią projektu)
```

## Licencja i pochodzenie

Wzorce ABI frameworka (konstruktor `PluginApp`, własna vtable, `Runnable`, `pluginAppInfo`) i sposób czytania CDS
pochodzą z NbtAad (<https://github.com/Sq00ky/Supra-iDrive6-Android-Auto>, PolyForm Noncommercial 1.0.0) i entry-aad,
więc ten projekt jest udostępniony na tej samej licencji: tylko do użytku niekomercyjnego. Biblioteki BMW
(`libAppFramework`, `libCoreFramework`) nie są częścią projektu.
