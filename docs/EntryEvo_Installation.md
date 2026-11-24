# GAUGE APP – instalacja na EntryNav2 (EntryEVO)

[English version](EntryEvo_Installation_EN.md)

Instalacja odbywa się ręcznie, przez SSH, kilkoma poleceniami. Nic w systemie nie jest zastępowane: dochodzi jeden
folder z aplikacją (`/opt/hmi/data/ro/Plugins/GaugeApp`) i jeden folder z danymi (`/var/local/data/GaugeApp`).
Partycja systemowa jest w trybie zapisu tylko na czas kopiowania.

> [!CAUTION]
> Przez całą instalację auto stoi, zapłon jest włączony. Nie wyłączaj zapłonu, gdy system jest w trybie zapisu
> (krok 3). W razie wątpliwości restart jednostki przywraca system tylko do odczytu.
>
> Ingerencja w jednostkę odbywa się na Twoją odpowiedzialność. Aplikacja niczego nie patchuje i zapisuje tylko we
> własnych folderach.

## Potrzebne

- Jednostka **EntryNav2** z dostępem **root przez SSH**.
- Komputer z klientem SSH (Windows 10/11 ma wbudowany OpenSSH, Linux, macOS).
- **Kabel ENET** między gniazdem OBD auta a komputerem. Karta sieciowa komputera zostaje na adresie automatycznym.
- Jedna z paczek z folderu `dist/` tego projektu:

| Paczka | Kiedy |
|---|---|
| `gauge-app-entrynav2.tar` | **Zwykła wersja** – GAUGE APP od razu pokazuje ekran z zegarami. |
| `gauge-app-entrynav2-diag.tar` | Tylko do diagnostyki: menu ze stronami testowymi (patrz [niżej](#wersja-diagnostyczna)). |

Obie paczki instaluje się tak samo. W poleceniach niżej nazwa paczki jest w zmiennej `P` – wpisz tę, którą
instalujesz (przykłady używają zwykłej wersji).

`169.254.1.0` to adres jednostki na kablu ENET w aucie, na którym to sprawdzano. Jeśli Twoja ma inny, zmień go w
poleceniach.

## 1. Skopiuj paczkę do auta

Na komputerze, w folderze projektu:

```sh
scp dist/gauge-app-entrynav2.tar root@169.254.1.0:/tmp/
ssh root@169.254.1.0
```

Wszystkie kolejne polecenia wpisujesz w tej sesji SSH, już na jednostce. `/tmp` jest w pamięci RAM: nic jeszcze nie
trafia do pamięci flash.

## 2. Sprawdź paczkę i jednostkę

W tym kroku nic nie jest zmieniane.

```sh
P=gauge-app-entrynav2.tar
cd /tmp && rm -rf gauge && mkdir gauge && tar -xf $P -C gauge && cd gauge
md5sum -c MD5SUMS
df -k /
```

- Każdy plik musi odpowiedzieć `OK`.
- W kolumnie `Available` musi być co najmniej ok. 20000 (KB) wolnego miejsca (paczka ma ok. 15 MB: klatki
  czterech ekranów, w czterech kolorach, i gotowe obrazki liczb). Przy aktualizacji stara wersja zwalnia swoje miejsce.

Teraz loader systemu sprawdzi, czy jednostka ma każdą bibliotekę i funkcję, której potrzebuje aplikacja, niczego
przy tym nie uruchamiając:

```sh
LD_TRACE_LOADED_OBJECTS=1 LD_WARN=yes LD_BIND_NOW=yes LD_LIBRARY_PATH=/usr/local/lib:/opt/hmi/lib:/usr/lib:/lib \
    /lib/ld-linux-armhf.so.3 ./opt/hmi/data/ro/Plugins/GaugeApp/libGaugeApp.so 2>&1 | grep -E 'not found|undefined symbol'
```

**To polecenie nie może nic wypisać.** Każda linia oznacza bibliotekę albo funkcję, której ta jednostka nie ma – wtedy
nie instaluj i prześlij tę linię.

## 3. Zainstaluj

```sh
mount -o remount,rw /
mkdir -p /opt/hmi/data/ro/Plugins/GaugeApp
rm -f /opt/hmi/data/ro/Plugins/GaugeApp/*
cp opt/hmi/data/ro/Plugins/GaugeApp/* /opt/hmi/data/ro/Plugins/GaugeApp/
chmod 755 /opt/hmi/data/ro/Plugins/GaugeApp/libGaugeApp.so
sync
mount -o remount,ro /
cd / && md5sum -c /tmp/gauge/MD5SUMS
```

- `rm -f` przed kopiowaniem jest celowe: iDrive trzyma starą bibliotekę w pamięci aż do restartu, a plik usunięty i
  skopiowany na nowo nie jest nadpisywany pod działającym programem.
- Ostatnie `md5sum -c` czyta zainstalowane pliki: każdy musi odpowiedzieć `OK`.
- Jeśli `mount -o remount,ro /` się nie uda, restart w następnym kroku i tak przywróci tryb tylko do odczytu.
- Biblioteka musi leżeć na partycji systemowej: `/var/local/data` jest zamontowany z `noexec`, więc iDrive nie
  załadowałby jej stamtąd. Folder danych tworzy sama aplikacja przy pierwszym starcie.

Posprzątaj i zrestartuj jednostkę:

```sh
rm -rf /tmp/gauge /tmp/gauge-app-entrynav2*.tar
reboot
```

## 4. Pierwsze uruchomienie

Po restarcie w menu **ConnectedDrive** powinien być wiersz **GAUGE APP** (`applicationType="OnlineServices"` w
`GaugeApp.xml`). iDrive czyta aplikacje tylko przy starcie, więc bez restartu wiersza nie będzie.

Wiersz z powrotem w menu **Media** (po Bluetooth audio, jak w starszych wersjach) – na komputerze
`python3 make_db.py --menu media --layout-only` i nowa paczka, albo od razu w aucie:

```sh
mount -o remount,rw /
sed -i 's/applicationType="OnlineServices"/applicationType="Custom"/' /opt/hmi/data/ro/Plugins/GaugeApp/GaugeApp.xml
sync
mount -o remount,ro /
reboot
```

### Wersja diagnostyczna

Wyniki diagnostyki w aucie (EntryNav2, F40):
- **diagnostyka 1** (T1–T5): etykiety działają, obrazki nie – przy bazie 635 obrazków (`onError 9`);
- **diagnostyka 2** (D1–D6): przy małej bazie działa wszystko – obrazek z bazy, ikona na przycisku, obrazek wysłany
  przez aplikację jako dane (raImage) i etykiety. Problemem była wielkość bazy obrazków;
- **diagnostyka 3** (E1–E4): pozycje x/y i nakładanie działają, widoczny obszar to ok. 1250 × 470 px, odświeżanie
  ok. 4,9 klatki/s działa płynnie, `onError 9` znika.

Dlatego zwykła wersja trzyma klatki w `GaugeApp_frames.bin` i wysyła je jako dane, a baza obrazków ma tylko ikonę.

Paczka `gauge-app-entrynav2-diag.tar` (budowana na żądanie: `python3 make_db.py --diag-out diag`,
`make entrynav2-diag-dist`) to **diagnostyka 3**:
GAUGE APP otwiera menu z czterema przyciskami. Wejdź w każdy i zrób zdjęcie **całego ekranu**:

| Przycisk | Co powinno być widać | Co to sprawdza |
|---|---|---|
| **E1** | karta „549 x 484”, na niej w lewym górnym rogu ikona zegara, druga ikona dalej w prawo (ok. 150 px niżej niż góra karty) | czy działają pozycje x/y i nakładanie obrazków (z bazy) |
| **E2** | to samo co E1 | to samo dla obrazków wysłanych jako dane |
| **E3** | siatka z liczbami co 100 px i czerwoną ramką, napis „1280 x 560” | jak duży obrazek mieści się na ekranie – z liczb przy krawędziach widać, ile pikseli jest widocznych |
| **E4** | karta z cyfrą 0–9 i niebieskim prostokątem, które zmieniają się 5 razy na sekundę | czy iDrive nadąża z płynnym odświeżaniem (najlepiej nagraj kilka sekund filmu) |

Prześlij:
1. zdjęcia stron E1–E4 (przy E3 tak, żeby było widać liczby przy prawej i dolnej krawędzi ekranu), przy E4 krótki film,
2. log aplikacji (patrz [niżej](#log)) – ważne są linie `diag: …`, zwłaszcza `diag: 50 animation frames in … ms`
   (pojawiają się, gdy strona E4 jest otwarta przez co najmniej 10 s).

Późniejsze ustalenie: iDrive pokazuje najwyżej ok. 60 obrazków w jednym stanie, dlatego ekran ma ich 47.

### Zwykła wersja

GAUGE APP otwiera ekran: płyn i olej po lewej, przeciążenie w środku z kafelkami biegów i paliwa pod nim, moc
i moment po prawej, z maksimami.
Zanim przyjdą pierwsze dane z auta (ok. 1,5 s), w miejscu wartości jest `--`.

W logu przy starcie powinny być linie:
- `settings: color=… temp=…` – wczytane ustawienia,
- `GaugeApp_frames.bin: … frames, … bytes` i `GaugeApp_frames_c0.bin: … frames` – aplikacja wczytała klatki ekranu
  (wspólne i w wybranym kolorze),
- `onInit: base onInit -> 1, 47 images written` – ekran został wysłany do iDrive,
- **brak** `onError 9` (ten błąd był skutkiem zbyt dużej bazy obrazków w starszych wersjach).

### Ustawienia (klawisz OPTION)

Na ekranie GAUGE APP naciśnij **OPTION** na kontrolerze iDrive i wybierz **Ustawienia**. Każde naciśnięcie
przycisku przełącza na następną wartość; zmiana jest od razu widoczna na ekranie i zapisuje się w
`/var/local/data/GaugeApp/settings.txt`:

| Przycisk | Wartości |
|---|---|
| Kolor wskaznikow | niebieski, czerwony, pomarańczowy BMW, zielony |
| Temperatura | stopnie Celsjusza, stopnie Fahrenheita |
| Moc | KM, kW, hp |
| Moment | Nm, lb-ft |
| Paliwo | litry, galony (US) |

Maksima są liczone w jednostkach bazowych (°C, KM, Nm), więc zmiana jednostek ich nie psuje – są tylko inaczej
pokazane. Paliwo (ilość w zbiorniku) ma własny kafelek obok biegów.

**Język** przełącza się sam razem z językiem iDrive: po polsku przy polskim, po angielsku przy każdym innym (tytuły,
„PS” zamiast „KM”, kropka dziesiętna). W logu widać to jako `CDS vehicle.language = '{"language":18}'` (18 = polski).

**Jeśli po instalacji zniknie wiersz GAUGE APP** (iDrive nie przyjął menu OPTION): usuń menu OPTION z XML i zrestartuj. Reszta (ekran, paliwo, zapisane ustawienia) działa dalej:

```sh
mount -o remount,rw /
sed -i '/<optionComponents>/,/<\/optionComponents>/d' /opt/hmi/data/ro/Plugins/GaugeApp/GaugeApp.xml
sync
mount -o remount,ro /
reboot
```

Prześlij zdjęcie ekranu na postoju i w czasie jazdy oraz log – posłużą do dopracowania układu, jednostek i
kierunków przeciążenia.

## Log

```sh
cat /var/local/data/GaugeApp/gauge-app.log
```

Log jest zawsze włączony i ma limit 512 KB (starszy trafia do `gauge-app.old.log`). Najważniejsze linie:

- `onInit: base onInit -> 1, 47 images written` – aplikacja wystartowała i ustawiła obrazki;
- `onError …` – błąd zgłoszony przez iDrive (np. `onError 9`);
- `CDS <nazwa> = '<wartość>' -> ok` – surowe dane z auta, pierwsze 5 odczytów każdej wartości.

Log można też zbierać na pendrive: utwórz na komputerze pusty plik `gauge-app.log` w głównym folderze pendrive'a i
włóż go do auta. Aplikacja szuka tego pliku w folderach pod `/media`, `/mnt` i `/run/media`.

## Aktualizacja i zmiana wersji

Powtórz kroki 1–3 z nową paczką (np. po diagnostyce z `gauge-app-entrynav2.tar`). Folder danych zostaje, więc
ustawienia nie giną.

## Maksima

Maksima płynu, oleju, mocy i momentu liczą się od zera przy każdym uruchomieniu aplikacji (czyli przy każdym
starcie iDrive). Maksima z ostatniego przejazdu zostają do wglądu w `/var/local/data/GaugeApp/max.txt`, np.:

```
coolant=98.0
oil=93.0
power=277.6
torque=419.0
```

Przy starcie są też zapisane w logu: `maxima reset (last run: coolant=98.0 oil=93.0 …)`.

## Wyłączenie i odinstalowanie

**Wyłączenie bez usuwania** (aplikacja nie wystartuje przy następnym uruchomieniu iDrive):

```sh
touch /var/local/data/GaugeApp/app.disable
reboot
```

Ponowne włączenie: `rm -f /var/local/data/GaugeApp/app.disable` i restart.

**Odinstalowanie:**

```sh
mount -o remount,rw /
rm -rf /opt/hmi/data/ro/Plugins/GaugeApp
sync
mount -o remount,ro /
rm -rf /var/local/data/GaugeApp
reboot
```

Bez ostatniego `rm -rf /var/local/data/GaugeApp` zostaną ustawienia na wypadek ponownej instalacji.

## W razie problemów

| Objaw | Co zrobić |
|---|---|
| Brak wiersza GAUGE APP w ConnectedDrive | Sprawdź krok 3 (`md5sum -c`) i zrestartuj jednostkę. Potem zajrzyj do logu: jeśli jest pusty, iDrive nie załadował biblioteki. |
| iDrive restartuje się kilka razy zaraz po starcie | Ochrona przed pętlą restartów wyłącza aplikację po 3 restartach iDrive w ciągu 2 minut od jej załadowania, a iDrive startuje dalej bez niej. Po sprawdzeniu logu: `rm -f /var/local/data/GaugeApp/app-guard`, restart. |
| Ekran GAUGE APP jest pusty | Sprawdź w logu linię `GaugeApp_frames.bin: … frames` – jeśli jest `cannot read …GaugeApp_frames.bin`, plik nie został skopiowany (krok 3). Potem prześlij log i zdjęcie. |
| Wszędzie `--` | Auto nie wysyła danych do aplikacji: po 25 s w logu będzie `no CDS value arrived…`. Prześlij log. |
| System został w trybie zapisu | `mount -o remount,ro /` albo restart jednostki. |
| Ekran iDrive nie reaguje | Przytrzymaj przycisk zasilania iDrive ok. 30 s, żeby zrestartować jednostkę. |
