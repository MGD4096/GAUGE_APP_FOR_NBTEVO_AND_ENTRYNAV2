# GAUGE APP – instalacja na NBT Evo

[English version](NbtEvo_Installation_EN.md)

Instalacja odbywa się ręcznie: pliki trafiają na jednostkę z pendrive'a albo przez SSH, a potem kilka poleceń
w powłoce jednostki. Nic w systemie nie jest zastępowane: dochodzi jeden folder z aplikacją
(`/opt/hmi/ID5/data/ro/Plugins/GaugeApp`) i jeden folder z danymi (`/var/opt/gaugeapp`). Partycja systemowa jest
w trybie zapisu tylko na czas kopiowania.

> [!CAUTION]
> Przez całą instalację auto stoi, zapłon jest włączony. Nie wyłączaj zapłonu, gdy system jest w trybie zapisu
> (krok 4). W razie wątpliwości restart jednostki przywraca system tylko do odczytu.
>
> Ingerencja w jednostkę odbywa się na Twoją odpowiedzialność. Aplikacja niczego nie patchuje i zapisuje tylko we
> własnych folderach.

> [!WARNING]
> Wersja NBT Evo **nie była jeszcze uruchomiona w aucie**. Wszystko, co dotyczy ekranu, sprawdzono na EntryNav2
> (F40). Na NBT niesprawdzone są: wielkość obszaru aplikacji (układ ma 1104×460 px), limit ok. 60 obrazków w jednym
> stanie, miejsce wiersza w menu (`OnlineServices` = ConnectedDrive), `vehicle.language` i kodowanie biegów. Pierwsze
> uruchomienie to test – patrz [Pierwsze uruchomienie](#5-pierwsze-uruchomienie).

## Potrzebne

- Jednostka **NBT Evo** (ID5 / ID6) z **powłoką root przez SSH**. Ta instrukcja nie opisuje, jak ją uzyskać.
- Jedno z kodowań **A4A, A4A_REMOTE_APPS, REMOTE_HMI, TOUCH_COMMAND** – bez niego HmiMain3D nie ładuje aplikacji
  PluginApp (tak samo jak dla NbtAad).
- Zbudowana aplikacja: folder **`dist\nbt\GaugeApp`** z `build_nbt.bat` (QNX Momentics IDE 4.7 / QNX SDP 6.5.0,
<<<<<<< Updated upstream
  patrz [README_PL.md](../README_PL.md#budowanie)). Powinno w nim być 10 plików:
=======
  patrz [README_PL.md](README_PL.md#budowanie)). Powinno w nim być 11 plików:
>>>>>>> Stashed changes

  | Plik | Co to |
  |---|---|
  | `libGaugeApp.so` | aplikacja |
  | `GaugeApp.manifest` | manifest dla iDrive |
  | `GaugeApp.xml` | wiersz w menu i ekrany |
  | `GaugeApp_ALL_Texts.zip`, `GaugeApp_ALL_Images.zip` | teksty i ikona wiersza |
  | `GaugeApp_frames.bin`, `GaugeApp_frames_s.bin`, `GaugeApp_frames_c0.bin` … `c3.bin` | klatki ekranów (ekran silnika, pozostałe ekrany i 4 kolory) |

- **Pendrive** (FAT32) **albo SSH z komputera**, żeby przenieść pliki na jednostkę.
- Ok. **26 MB** wolnego miejsca na partycji systemowej.

## 1. Przenieś pliki na jednostkę

### Sposób A: pendrive (zalecany)

1. Na komputerze skopiuj folder `GaugeApp` (z `dist\nbt`) do głównego katalogu pendrive'a.
2. Włóż pendrive do portu USB w aucie, przy włączonym zapłonie.

Pliki będą w `/fs/usb0/GaugeApp`. Jeśli `ls /fs/usb0` nic nie pokazuje, sprawdź `ls /mnt` – pendrive może być
w folderze `umass…`; wtedy w poleceniach niżej użyj go zamiast `/fs/usb0`.

### Sposób B: przez SSH, bez pendrive'a

Jednostka nie ma `scp` ani `sftp`, więc każdy plik idzie przez `cat`. `root@CAR` zastąp swoim sposobem logowania;
jeśli klient SSH odrzuca klucz hosta, dodaj `-o HostKeyAlgorithms=+ssh-rsa`. Z folderu `dist\nbt` na komputerze
(np. w Git Bash lub WSL):

```sh
ssh root@169.254.199.99 -o HostKeyAlgorithms=+ssh-rsa -m hmac-sha1
ssh root@CAR 'mkdir -p /net/hu-omap/fs/ram5/GaugeApp'
for f in GaugeApp/*; do
  ssh root@CAR "cat > /net/hu-omap/fs/ram5/$f" < "$f"
done
```

To 11 logowań. Jednostka po wielu logowaniach w krótkim czasie wyłącza SSH na ok. 10 minut, więc nie powtarzaj pętli
kilka razy. Pliki trafiają do `/tmp/GaugeApp` na `hu-omap` – to RAM, czyszczony przy restarcie, więc dokończ
instalację przed wyłączeniem auta.

## 2. Zaloguj się na właściwy komputer jednostki

SSH otwiera powłokę na `hu-jacinto`, a iDrive (HmiMain3D) działa na drugim komputerze, `hu-omap`. Przejdź na niego:

```sh
on -f /net/hu-omap/ /bin/sh
```

Wszystkie dalsze polecenia wpisujesz w tej powłoce. Ustaw, skąd biorą się pliki:

```sh
SRC=/fs/usb0/GaugeApp        # pendrive
SRC=/tmp/GaugeApp            # albo: przez SSH
```

(wpisz tylko jedną z tych linii).

## 3. Sprawdź pliki i miejsce

Nic nie jest zmieniane w tym kroku.

```sh
ls -l $SRC
df -h /fs/sda0
```

- W `$SRC` musi być 11 plików z tabeli wyżej; `libGaugeApp.so` ma kilkadziesiąt KB, `GaugeApp_frames.bin` ok. 6 MB, `GaugeApp_frames_s.bin` ok. 9 MB.
- Na `/fs/sda0` musi być co najmniej ok. 26 MB wolnego miejsca.

## 4. Zainstaluj

```sh
/bin/mount -u -o rw /fs/sda0
mkdir -p /opt/hmi/ID5/data/ro/Plugins/GaugeApp
rm -f /opt/hmi/ID5/data/ro/Plugins/GaugeApp/*
cp $SRC/* /opt/hmi/ID5/data/ro/Plugins/GaugeApp/
chmod 755 /opt/hmi/ID5/data/ro/Plugins/GaugeApp/libGaugeApp.so
ls -l /opt/hmi/ID5/data/ro/Plugins/GaugeApp
/bin/mount -u -o ro /fs/sda0
```

- `rm -f` przed kopiowaniem jest celowe: iDrive trzyma starą bibliotekę w pamięci aż do restartu, a plik usunięty
  i skopiowany na nowo nie jest nadpisywany pod działającym programem.
- `ls -l` po kopiowaniu musi pokazać te same 11 plików i te same rozmiary co w kroku 3.
- Jednostka nie zapisuje wszystkiego na żądanie: zostaw ją włączoną jeszcze ok. minuty, zanim wyłączysz zapłon.
- Folder danych `/var/opt/gaugeapp` (ustawienia, maksima) tworzy sama aplikacja przy pierwszym starcie.

Potem zrestartuj jednostkę: przytrzymaj przycisk zasilania iDrive ok. 30 s albo wyłącz auto, aż jednostka się
wyłączy, i włącz ponownie. iDrive czyta aplikacje tylko przy starcie.

## 5. Pierwsze uruchomienie

Po restarcie w menu **ConnectedDrive** powinien być wiersz **GAUGE APP**. Jeśli go nie ma, sprawdź menu **Media**
oraz [W razie problemów](#w-razie-problemów).

GAUGE APP otwiera ekran: płyn i olej po lewej, przeciążenie, bieg i paliwo w środku, moc i moment po prawej. Zanim
przyjdą pierwsze dane z auta (ok. 1,5 s), w miejscu wartości jest `--`.

Ponieważ to pierwsze uruchomienie wersji NBT, prześlij:

1. **zdjęcie całego ekranu GAUGE APP** – widać na nim, czy układ mieści się w obszarze aplikacji i czy pokazują się
   wszystkie elementy (także przeciążenie, biegi i paliwo – na EntryNav2 elementy powyżej ok. 60. zostawały puste),
2. **log** (patrz [Log](#log)),
3. gdzie pojawił się wiersz GAUGE APP (ConnectedDrive, Media, nigdzie).

Jeśli ekran jest za duży albo przesunięty, układ zmienia się w `make_db.py` (`SCALE`, `--x`, `--y`), bez zmian
w kodzie.

### Ustawienia (klawisz OPTION)

Na ekranie GAUGE APP naciśnij **OPTION** i wybierz **Ustawienia**. Każde naciśnięcie przycisku przełącza na
następną wartość; zmiana jest od razu widoczna i zapisuje się w `/var/opt/gaugeapp/settings.txt`:

| Przycisk | Wartości |
|---|---|
| Kolor wskaznikow | niebieski, czerwony, pomarańczowy BMW, zielony |
| Temperatura | stopnie Celsjusza, stopnie Fahrenheita |
| Moc | KM, kW, hp |
| Moment | Nm, lb-ft |
| Paliwo | litry, galony (US) |

**Język** przełącza się sam z językiem iDrive (`vehicle.language`): polski przy polskim, angielski przy każdym innym.

**Maksima** płynu, oleju, mocy i momentu liczą się od zera przy każdym starcie aplikacji. Te z ostatniego przejazdu
zostają w `/var/opt/gaugeapp/max.txt`.

## Log

Wersja NBT pisze do logu systemowego:

```sh
sloginfo | grep GaugeApp
```

Łatwiej: utwórz na komputerze **pusty plik `gauge-app.log`** w głównym folderze pendrive'a i włóż go do auta – log
będzie dopisywany tam (limit 4 MB). Aplikacja szuka go w `/fs/usb*` i `/mnt/umass*`.

Najważniejsze linie przy starcie:

- `library loaded …` i `create: app …` – iDrive załadował aplikację,
- `settings: color=… temp=…` – wczytane ustawienia,
- `GaugeApp_frames.bin: … frames` i `GaugeApp_frames_c0.bin: … frames` – wczytane klatki ekranu,
- `onInit: base onInit -> 1, … images written` – ekran wysłany do iDrive,
- `onError …` – błąd zgłoszony przez iDrive (na EntryNav2 `onError 9` oznaczał zbyt dużą bazę obrazków),
- `CDS <nazwa> = '<wartość>' -> ok` – surowe dane z auta, pierwsze 5 odczytów każdej wartości
  (`driving.gear`, `driving.acceleration`, `vehicle.language`… – potrzebne do sprawdzenia NBT).

Po 25 s bez żadnych danych z auta w logu pojawi się `no CDS value arrived…`.

## Aktualizacja

Zbuduj nową wersję (`build_nbt.bat`) i powtórz kroki 1–4. Ustawienia w `/var/opt/gaugeapp` zostają.

## Wyłączenie i odinstalowanie

**Wyłączenie bez usuwania** (aplikacja nie wystartuje przy następnym uruchomieniu iDrive). Jednostka nie ma
`touch`, więc:

```sh
mkdir -p /var/opt/gaugeapp
echo off > /var/opt/gaugeapp/app.disable
```

i restart. Ponowne włączenie: `rm /var/opt/gaugeapp/app.disable` i restart.

**Odinstalowanie:**

```sh
/bin/mount -u -o rw /fs/sda0
rm -rf /opt/hmi/ID5/data/ro/Plugins/GaugeApp
/bin/mount -u -o ro /fs/sda0
rm -rf /var/opt/gaugeapp
```

i restart. Bez ostatniego `rm -rf /var/opt/gaugeapp` zostaną ustawienia na wypadek ponownej instalacji.

## W razie problemów

| Objaw | Co zrobić |
|---|---|
| Brak wiersza GAUGE APP w ConnectedDrive | Sprawdź menu Media i kodowanie (A4A / REMOTE_HMI…). Sprawdź krok 4 (`ls -l`) i log: brak `library loaded` = iDrive nie załadował aplikacji. Wiersz w Media zamiast ConnectedDrive: na komputerze `python3 make_db.py --menu media --layout-only` i nowy `GaugeApp.xml` |
| Ekran GAUGE APP jest pusty | W logu sprawdź `GaugeApp_frames.bin: … frames` – `cannot read …` oznacza brak pliku (krok 4). Potem prześlij log i zdjęcie |
| Część ekranu pusta, reszta działa | Limit obrazków w stanie może być na NBT inny niż na EntryNav2 (ok. 60). Prześlij zdjęcie – widać, od którego elementu brakuje |
| Ekran za duży, ucięty albo przesunięty | Obszar aplikacji na NBT ma inną wielkość. Prześlij zdjęcie; układ zmienia się w `make_db.py` (`SCALE`, `--x`, `--y`) |
| Wszędzie `--` | Auto nie wysyła danych do aplikacji: w logu `no CDS value arrived…`. Prześlij log |
| Zły bieg w D | Na EntryNav2 auto wysyła bieg skrzyni + 4. Prześlij linie `CDS driving.gear` z logu z jazdy na D1 / D2 |
| iDrive nie wstaje po instalacji | Wyłącz aplikację (`echo off > /var/opt/gaugeapp/app.disable`) i zrestartuj. Jeśli to nie pomaga, przenieś folder aplikacji: `/bin/mount -u -o rw /fs/sda0`, `mv /opt/hmi/ID5/data/ro/Plugins/GaugeApp /opt/GaugeApp.off`, `/bin/mount -u -o ro /fs/sda0`, restart. Prześlij log |
| Ekran iDrive nie reaguje | Przytrzymaj przycisk zasilania iDrive ok. 30 s, żeby zrestartować jednostkę |
