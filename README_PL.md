# Startowy projekt, napisany za pomocą Claude
Działa, ale czasami może zawiesić główną jednostkę (head unit) albo to zależy od mojej konfiguracji. W ciągu najbliższych kilku dni przetestuję to rozwiązanie bardziej szczegółowo.
![NBTEvo with running app](/images/20261105_220049.jpg)


# IDRIVE GAUGE APP – dane silnika na ekranie iDrive

Natywna aplikacja iDrive (ID5/ID6, QNX) pokazująca na żywo: **temperaturę wody, temperaturę oleju, obroty, prędkość,
bieg, poziom paliwa i zasięg oraz temperaturę zewnętrzną**. Pojawia się jako wiersz **„Dane silnika”** w menu
Media/Radio (zaraz po wierszu Bluetooth audio, w tym samym miejscu, w którym repozytorium Supra-iDrive6-Android-Auto
umieszcza „Android Auto” – to miejsce jest tam sprawdzone na aucie).

```
Woda: 92 °C
Olej: 104 °C
Obroty: 2450 obr/min
Prędkość: 87 km/h
Bieg: D3
Paliwo: 39 l, zasięg: 522 km
Temp. zewn.: 14,0 °C
```

Nie wymaga demona Android Auto ani niczego poza samą aplikacją. Identyfikatory są dobrane tak, żeby dało się ją
zainstalować obok NbtAad (niesprawdzone na aucie).

## Jak to działa

HmiMain3D przy starcie ładuje `Plugins/<Nazwa>/<Nazwa>.manifest` (framework `PluginApp`, ten sam co w BMW
SecurityMenu / ActiveSeating i w NbtAad). `GaugeApp.xml` opisuje wiersz menu i jeden ekran z siedmioma etykietami
(`label`), każda związana z modelem tekstowym `raDataModel`. `libGaugeApp.so`:

1. po ok. 1,5 s od startu subskrybuje właściwości **CDS** (Car Data Service) – tym samym wywołaniem
   `cdsAddPropertyChangedEventHandler`, którym NbtAad czyta `driving.gear` i `sensors.PDCStatus`;
2. trzyma ostatnie wartości; co 500 ms formatuje wiersze i przez `PluginApp::updateModel(model, tekst)` zapisuje
   **tylko te, które się zmieniły**;
3. gdy wartość jest niedostępna, błędna lub nierealna (np. `{"error":400}`), wiersz pokazuje `--`.

| Właściwość CDS | Przykładowa wartość | Wiersz |
|---|---|---|
| `engine.temperature` | `{"temperature":{"engine":19,"oil":18}}` | Woda, Olej |
| `engine.RPMSpeed` | `{"RPMSpeed":2453}` | Obroty (zaokrąglone do 10) |
| `driving.speedActual` | `{"speedActual":87}` | Prędkość |
| `driving.gear` | `{"gear":6}` | Bieg (1 N, 2 R, 3 P, 4+ D1…) |
| `sensors.fuel` | `{"fuel":{"range":522,"reserve":0,"tanklevel":39}}` | Paliwo, zasięg |
| `sensors.temperatureExterior` | `{"temperatureExterior":14.0}` | Temp. zewn. |

Nazwy i formaty: <https://bimmergestalt.github.io/BMWConnectedAnalysis/cds/>.

## Co jest sprawdzone, a co nie

**Sprawdzone (na hoście):**
- Logika parsowania i formatowania (`tests/test_cds_values.cpp`) oraz cały cykl życia aplikacji: ładowanie przez
  `pluginAppInfo`, `onInit`, subskrypcja sześciu właściwości, odświeżanie tylko zmienionych wierszy, błędne dane,
  `onFinalize` (`tests/app_host_test.cpp`, na atrapie frameworka). `make check`.
- Wszystkie 10 symboli `bmw::…`, których biblioteka używa, jest eksportowane przez `libAppFramework.A.so` /
  `libCoreFramework.A.so` z auta (sprawdzone `nm -D`), w tym `updateModel(unsigned, BasicString<unsigned short> const&)`.
- XML-e są poprawne składniowo, a identyfikatory modeli i etykiet są spójne z kodem.

**Niesprawdzone – do potwierdzenia na aucie (pierwsze uruchomienie to test):**
- **Kompilacja `qcc`.** W tym środowisku nie ma QNX SDP 6.5; kod jest C++98 i buduje się `g++ -std=gnu++98`, ale
  kompilacja docelowa (ARMv7, GCC 4.4) nie była uruchomiona.
- **`label` + `raDataModel` w XML PluginApp.** NbtAad używa w XML tylko przycisków, checkboksów, obrazów, listy
  Richtext i `textIdModel`; `label`/`raDataModel` pochodzą z dokumentacji RHMI (BimmerGestalt), a przeciążenie
  `updateModel` z tekstem istnieje we frameworku. To największe ryzyko: jeśli HmiMain3D odrzuci XML, wiersza po prostu
  nie będzie.
- **Czy auto publikuje `engine.*` / `sensors.*` aplikacjom pluginowym.** W NbtAad potwierdzone są `driving.gear`,
  `sensors.PDCStatus`, `driving.mode`, `vehicle.dayNightChangeOver`, `communication.callStatusN`.
- **Znaczenie `engine.temperature.engine`.** Dokumentacja CDS nie mówi wprost, że to płyn chłodzący; porównaj z
  zegarem w kokpicie.
- **Mapowanie biegów** (1 N, 2 R, 3 P, 4+ D) pochodzi z dokumentacji; w manualu wartości mogą być inne – surowa
  wartość trafia do logu.
- Dwie wartości, które wybrałem sam: `entryButtonFocusID="32751"` (NbtAad ma 32752) i `<id>211</id>` w manifeście
  (NbtAad ma 210), żeby aplikacje się nie zderzały. Jeśli menu się nie pojawia, zmień je.
- Kod języka `pl` w bazie tekstów (reszta języków jak w NbtAad). Przy innym języku iDrive tytuł wiersza może być pusty.

> Ingerencja w head unit odbywa się na Twoją odpowiedzialność (jak w NbtAad: po błędzie reflash robi tylko
> BMW/Toyota). Aplikacja niczego nie patchuje ani nie zapisuje na partycjach systemowych poza własnym folderem
> w `Plugins`.

## Wymagania

Takie same jak NbtAad: dostęp root/SSH do NBT Evo oraz jedno z kodowań **A4A, A4A_REMOTE_APPS, REMOTE_HMI,
TOUCH_COMMAND** (bez tego HmiMain3D nie ładuje PluginApps). Do budowy: QNX SDP 6.5 (`qcc`) oraz kopie
`libAppFramework.A.so` i `libCoreFramework.A.so` z Twojego head unit (`/opt/hmi/ID5/lib`).

## Budowanie

```
cp /sciezka/do/libAppFramework.A.so /sciezka/do/libCoreFramework.A.so lib/     # z auta
make            # libGaugeApp.so + GaugeApp_ALL_Texts.zip + GaugeApp_ALL_Images.zip
make check      # testy hostowe (zwykły g++, bez QNX)
```

(`make db` buduje same bazy – `python3` + Pillow. Można też użyć `build.sh` z repozytorium NbtAad w kontenerze QNX.)

## Instalacja

Na head unit, pliki z pendrive'a (`/mnt/umass…` – sprawdź `ls /mnt`):

```
mkdir -p /opt/hmi/ID5/data/ro/Plugins/GaugeApp
cp /mnt/umassXXXX/libGaugeApp.so /opt/hmi/ID5/data/ro/Plugins/GaugeApp/
cp /mnt/umassXXXX/GaugeApp.manifest /opt/hmi/ID5/data/ro/Plugins/GaugeApp/
cp /mnt/umassXXXX/GaugeApp.xml /opt/hmi/ID5/data/ro/Plugins/GaugeApp/
cp /mnt/umassXXXX/GaugeApp_ALL_Texts.zip /opt/hmi/ID5/data/ro/Plugins/GaugeApp/
cp /mnt/umassXXXX/GaugeApp_ALL_Images.zip /opt/hmi/ID5/data/ro/Plugins/GaugeApp/
```

Jeśli kopiowanie kończy się „read-only file system”, przemontuj cel do zapisu tak samo, jak przy NbtAad
(`install.md`). Potem przytrzymaj przycisk zasilania ok. 30 s (restart). W **Media/Radio** powinien być wiersz
**Dane silnika**.

**Aktualizacja:** nie nadpisuj działającej biblioteki – `mv libGaugeApp.so libGaugeApp.so.old`, skopiuj nową,
zrestartuj. **Odinstalowanie:** usuń folder `Plugins/GaugeApp` i zrestartuj. **Wyłącznik awaryjny bez usuwania:**
`mkdir -p /var/opt/engine && touch /var/opt/engine/app.disable` (`/opt/engine/app.disable` też działa, ale `/opt`
bywa tylko do odczytu).

## Diagnostyka

Aplikacja loguje przez `slog` (kod 0x4e47; `sloginfo | grep GaugeApp`). Łatwiej: **utwórz na komputerze pusty plik
`nbt-engine-data.log` na pendrivie** i włóż go do auta – log będzie dopisywany tam (limit 4 MB).

Każda właściwość CDS jest zapisana w logu w surowej postaci przy pierwszych 5 odczytach, np.
`CDS engine.temperature = '{"temperature":{"engine":92,"oil":104}}' -> ok`. To dokładnie to, czego potrzeba, żeby
sprawdzić, co Twoje auto naprawdę wysyła.

**Brak danych (wszędzie `--`):** wiersz menu jest, ale wartości nie przychodzą – 25 s po starcie w logu pojawi się
komunikat `no CDS value arrived…`. Znaczy to, że auto nie publikuje tych właściwości aplikacjom pluginowym albo
subskrypcja się nie powiodła. Prześlij fragment logu – można wtedy spróbować innych nazw właściwości lub
odczytu z innego źródła.

**Brak wiersza w menu:** sprawdź kodowanie (A4A itd.), obecność wszystkich 5 plików, ewentualny konflikt
`entryButtonFocusID` / `<id>` w manifeście oraz log HMI. Jeśli XML jest odrzucany, zacznij od zdjęcia `label`
z `GaugeApp.xml` i sprawdzenia samego wiersza.

## Dostosowanie

- **Teksty i język wierszy:** makra `ENG_TXT_*` na górze sekcji „display rows” w `src/cds_values.hpp`
  (UTF-8; escape'y zapisane jako osobne literały).
- **Nowa wartość:** dodaj pozycję w `enum Prop` i `propName`, regułę w `apply()`, wiersz w `formatRows`, kolejny
  `raDataModel` + `label` w `GaugeApp.xml` (ID 28 / 38…), zwiększ `kRowCount`, `kPropCount` i tablicę `kStubs`.
- **Częstotliwość odświeżania:** `kRenderMs` w `src/engine_data.cpp`.

## Wersja na EntryNav2 (EntryEVO)

Ta sama aplikacja, z tych samych źródeł, w wersji na **EntryNav2** (Linux ARMv7 hard-float, glibc 2.15). Sposób
osadzenia w iDrive jest wzorowany na projekcie entry-aad (Android Auto dla EntryNav2), który działa w aucie jako
PluginApp: ten sam konstruktor `PluginApp`, ta sama vtable (34 sloty, onError 21 / onInit 22 / onFinalize 23), ta sama
subskrypcja CDS, to samo miejsce w menu (stan 20, po wierszu 2270). Identyfikatory różnią się od entry-aad
(`entryButtonFocusID` 32751 / 32752, `<id>` 211 / 210), więc obie aplikacje mogą być zainstalowane razem.

Różnice względem NBT Evo (wszystko w `#ifdef GAUGE_ENTRYNAV2` w `src/engine_data.cpp`):

| | NBT Evo | EntryNav2 |
|---|---|---|
| System / kompilator | QNX 6.5, `qcc` (GCC 4.4) | Linux armhf, `arm-linux-gnueabihf-g++` 4.6 (eglibc 2.15) |
| Folder aplikacji | `/opt/hmi/ID5/data/ro/Plugins/GaugeApp` | `/opt/hmi/data/ro/Plugins/GaugeApp` |
| Biblioteki BMW do linkowania | `/opt/hmi/ID5/lib` | `/opt/hmi/lib` (inne pliki niż z NBT Evo!) |
| Log | `slog` + pendrive | `/var/local/data/GaugeApp/gauge-app.log` (max 512 KB, zawsze) + pendrive |
| Wyłączenie | `/var/opt/gaugeapp/app.disable` | `/var/local/data/GaugeApp/app.disable` |
| Ochrona przed pętlą restartów | brak | 3 restarty HMI w < 2 min po załadowaniu → aplikacja się wyłącza |
| `updateModel(tekst)` | wywołanie bezpośrednie (sprawdzone `nm -D`) | szukane przez `dlsym`; brak → puste wiersze, iDrive działa dalej |

**Sprawdzone `nm -D` na kopii bibliotek z EntryNav2 (`lib/Entry_Evo_libs`):** wszystkie symbole używane przez
aplikację są eksportowane, także `bmw::PluginApp::updateModel(unsigned, BasicString<unsigned short> const&)`
(libAppFramework) i konstruktor `BasicString<unsigned short>(unsigned short const*)` (libCoreFramework). entry-aad
nigdy nie zapisuje tekstu do modelu, więc samo wywołanie w aucie nie jest jeszcze sprawdzone; biblioteka nadal szuka
tych funkcji w czasie działania i zapisuje w logu `text model API: ... -> ok` albo `-> MISSING`. Sprawdzenie na innej
wersji oprogramowania:

```
nm -D --defined-only /opt/hmi/lib/libAppFramework.A.so /opt/hmi/lib/libCoreFramework.A.so | \
    grep -E '_ZN3bmw9PluginApp11updateModelEjRKNS_11BasicStringItEE|_ZN3bmw11BasicStringItEC1EPKt|_ZN3bmw11BasicStringItED1Ev'
```

Powinny być wszystkie trzy. Jak na NBT Evo, niesprawdzone są też `label` + `raDataModel` w XML i to, czy auto
publikuje `engine.*` / `sensors.*` aplikacjom (entry-aad potwierdza `driving.gear`, `communication.callStatus*`,
`vehicle.dayNightChangeOver`, `driving.mode`).

### Budowanie (EntryNav2)

Potrzebne są kopie `libAppFramework.A.so` i `libCoreFramework.A.so` z `/opt/hmi/lib` auta w `lib/Entry_Evo_libs`
(pełna kopia systemu nie jest potrzebna) i obraz Dockera z `toolchain/Dockerfile` (Ubuntu 12.04: armhf GCC 4.6 i
eglibc 2.15, ta sama wersja co w aucie). Obraz entry-aad (`FROM ubuntu:12.10`) nie buduje się już w aktualnym Dockerze
(stary format manifestu). Kompilator musi pasować do glibc 2.15 auta: nowszy armhf GCC z Ubuntu podlinkuje np.
`clock_gettime@GLIBC_2.17`, którego auto nie ma. Zbudowana biblioteka wymaga tylko `GLIBC_2.4`.

```
docker build -t gauge-entrynav2-tc toolchain        # raz
bash toolchain/tc-entrynav2.sh make entrynav2-dist
make check                                          # testy hostowe obu wersji
```

Na Windowsie bez basha: `docker run --rm -v "%CD%:/work" -w /work gauge-entrynav2-tc make entrynav2-dist`.

Wynik: `build/entrynav2/libGaugeApp.so` i `dist/gauge-app-entrynav2.tar` (biblioteka, manifest, XML, dwa zipy,
`MD5SUMS`). Bez Dockera: `make entrynav2 EN2_CXX=arm-linux-gnueabihf-g++ EN2_LIBDIR=<folder z bibliotekami EntryNav2>`.

### Instalacja (EntryNav2)

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

- Polecenie z `LD_TRACE_LOADED_OBJECTS` nie może nic wypisać (linia = brakująca biblioteka lub funkcja).
- Folder `/var/local/data` jest zamontowany z `noexec`, dlatego biblioteka musi leżeć na partycji systemowej.
- W **Media** powinien pojawić się wiersz **GAUGE APP**.

**Log:** `cat /var/local/data/GaugeApp/gauge-app.log`. Można też położyć pusty plik `gauge-app.log` na pendrivie –
biblioteka szuka go w każdym folderze bezpośrednio pod `/media`, `/mnt` i `/run/media` (punkt montowania pendrive’a
na EntryNav2 nie jest pewny).

**Wyłączenie bez kasowania:** `mkdir -p /var/local/data/GaugeApp && touch /var/local/data/GaugeApp/app.disable`.
**Po zadziałaniu ochrony przed pętlą restartów:** sprawdź log, potem `rm -f /var/local/data/GaugeApp/app-guard` i
restart. **Odinstalowanie:** `mount -o remount,rw /`, `rm -rf /opt/hmi/data/ro/Plugins/GaugeApp`, `sync`,
`mount -o remount,ro /`, `rm -rf /var/local/data/GaugeApp`, `reboot`.

## Układ projektu

```
src/cds_values.hpp     parsowanie CDS i formatowanie wierszy (czysta logika, testowana)
src/engine_data.cpp    aplikacja: PluginApp, subskrypcja CDS, odświeżanie etykiet (NBT Evo i EntryNav2)
GaugeApp.xml         wiersz menu + ekran z 7 etykietami (wspólny)
GaugeApp.manifest    manifest dla CAppManager (wspólny)
make_db.py             bazy tekstów i obrazów (+ ikona 63x54, wspólne)
toolchain/tc-entrynav2.sh  uruchamia polecenie w obrazie entrynav2-tc:4.7 (EntryNav2)
tests/                 testy hostowe i atrapa frameworka (obie wersje)
```

## Licencja i pochodzenie

Wzorce ABI frameworka (konstruktor `PluginApp`, własna vtable, `Runnable`, `pluginAppInfo`) i sposób czytania CDS
pochodzą z NbtAad (<https://github.com/Sq00ky/Supra-iDrive6-Android-Auto>, PolyForm Noncommercial 1.0.0), więc ten
projekt jest udostępniony na tej samej licencji: tylko do użytku niekomercyjnego. Biblioteki BMW
(`libAppFramework`, `libCoreFramework`) nie są częścią projektu.
