# EntryNav2 – what we know about the head unit

What was found out about the EntryNav2 (EntryEVO) head unit in a BMW F40 while working on GaugeApp and CdsScan:

- [System.md](System.md): hardware, system, folders, processes, HMI, where the CDS data comes from, useful commands.
- [PluginApp.md](PluginApp.md): the iDrive app framework (manifest, entry point, `bmw::PluginApp` functions,
  screen XML, limits checked in the car, good practice).
- [CDS.md](CDS.md): all 263 CDS names with their JSON format, the result of a scan in the car and notes.

Installing the app: [../EntryEvo_Installation.md](../EntryEvo_Installation.md). CDS scanning tool:
`C:\Dev\BMW_Navi\HU_Tools\CdsScan`.

These files contain no personal data from the car (contacts, position, VIN). BMW files (libraries, `HmiMain3D`) are
not part of the project.
