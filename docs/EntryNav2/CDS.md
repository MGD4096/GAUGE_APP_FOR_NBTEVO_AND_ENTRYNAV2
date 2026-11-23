# CDS on EntryNav2 – property list

Every CDS name the EntryNav2 HMI knows (the registry of `TPCI::CCdsProperty*` classes and names in `/opt/app/usr/hmi/data/ro/hmiplugins/libhmiremoting.so`), plus those of the [BimmerGestalt](https://bimmergestalt.github.io/BMWConnectedAnalysis/cds/) list. 263 names in all.

- **Format** is the `printf` template `libhmiremoting.so` builds the value with (JSON, in UTF-16). `%hu`/`%u` = unsigned number, `%d`/`%hd` = signed, `%1.1f` = 1 decimal place, `%s` = text.
- **Scan** is the result of CdsScan 0.1 on an EntryNav2 in a BMW F40 (22.11.2026, 1.2 min, standing and manoeuvring, cold engine, 103 names). Statuses:
  - ✅ data arrived – the first value or the range is given;
  - ⛔ `{"error":401}` / `400` – the car knows the name but does not support it;
  - ∅ no answer (unknown name, or nothing changed);
  - ? not scanned yet (names added from the registry; CdsScan 0.2 subscribes to all of them);
  - 🚫 left out by CdsScan on purpose (commands, typed text, Wi-Fi password).
- The first value after subscribing is the current state; after that only changes arrive. 255 / 65535 / 4095 / −32768 usually mean "no value". Personal data (calls, contacts, position, VIN) is left out here.
- Values and their meaning in the "Notes" column come from observation – where there is a "?", it is a guess.

## atm

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `atm.atmSettings` | `{"atmSettings":{"ssid":"%s","key":"%s","accessPointOn":%d,"ssidVisible":%d}}` | 🚫 | contains the Wi-Fi password – CdsScan does not subscribe to it |

## cds

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `cds.apiRegistry` | `{"apiRegistry":{"message":"clientCountChanged","value":%u}}` | ∅ | no data – it is not a list of the properties |

## climate

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `climate.ACCompressor` | `{"ACCompressor":%d}` | ✅ 0 |  |
| `climate.ACMode` | `{"ACMode":{"maxCool":%d,"recirculation":%d,"defrost":%d}}` | ✅ maxCool 0, recirculation 0, defrost 0 |  |
| `climate.ACSystemTemperatures` | `{"ACSystemTemperatures":{"evaporator":%d,"heatExchanger":%d}}` | ✅ evaporator 6, heatExchanger 5 (°C) |  |
| `climate.airConditionerCompressor` | `{"airConditionerCompressor":{"actualPower":%hu,"dualMode":%d,"actualTorque":%hu}}` | ✅ actualPower 255→0, dualMode 3, actualTorque 255→0 (255 = no value) |  |
| `climate.armRestHeating` | `{"armRestHeating":{"levelDR":%u,"levelPS":%u,"levelDRR":%u,"levelPSR":%u}}` | ? |  |
| `climate.driverSettings` | `{"driverSettings":{"desiredTemperature":%1.1f,"program":%hu,"automaticBlower":%d}}` | ✅ desiredTemperature 22.0, program 43, automaticBlower 0 |  |
| `climate.fondSettings` | `{"fondSettings":{"airDistribution":%u,"blower":%u,"mode":%u,"buttonMaxAC":%u,"tempLeft":%0.1f,"tempRight":%0.1f}}` | ? |  |
| `climate.passengerSettings` | `{"passengerSettings":{"desiredTemperature":%1.1f,"program":%hu,"automaticBlower":%d}}` | ✅ desiredTemperature 22.0, program 63, automaticBlower 0 |  |
| `climate.residualHeat` | `{"residualHeat":%d}` | ✅ 0 |  |
| `climate.seatAutoClimateDR` | `{"seatAutoClimateDR":{"heaterControl":%u,"heaterStage":%u,"heaterThreshold":%u,"ventilationControl":%u,"ventilationStage":%u,"ventilationThreshold":%u,"steeringWheelHeating":%u,"steeringWheelHeatingThreshold":%u,"tempMeasurement":%u}}` | ? |  |
| `climate.seatAutoClimateDRR` | `{"seatAutoClimateDRR":{"heaterControl":%u,"heaterStage":%u,"heaterThreshold":%u,"ventilationControl":%u,"ventilationStage":%u,"ventilationThreshold":%u,"tempMeasurement":%u}}` | ? |  |
| `climate.seatAutoClimatePS` | `{"seatAutoClimatePS":{"heaterControl":%u,"heaterStage":%u,"heaterThreshold":%u,"ventilationControl":%u,"ventilationStage":%u,"ventilationThreshold":%u,"tempMeasurement":%u}}` | ? |  |
| `climate.seatAutoClimatePSR` | `{"seatAutoClimatePSR":{"heaterControl":%u,"heaterStage":%u,"heaterThreshold":%u,"ventilationControl":%u,"ventilationStage":%u,"ventilationThreshold":%u,"tempMeasurement":%u}}` | ? |  |
| `climate.seatClimate` | `{"seatClimate":{"HeatingLaminationDR":%d,"HeatingLaminationPS":%d,"HeatingLaminationDRR":%d,"HeatingLaminationPSR":%d}}` | ? |  |
| `climate.seatClimateDRR` | `{"seatClimateDRR":%d}` | ? |  |
| `climate.seatClimatePassenger` | `{"seatClimatePassenger":%d}` | ? |  |
| `climate.seatClimatePSR` | `{"seatClimatePSR":%d}` | ? |  |
| `climate.seatHeatDriver` | `{"seatHeatDriver":%d}` | ✅ 0 |  |
| `climate.seatHeatDRR` | `{"seatHeatDRR":%d}` | ? |  |
| `climate.seatHeatPassenger` | `{"seatHeatPassenger":%d}` | ✅ 0 |  |
| `climate.seatHeatPSR` | `{"seatHeatPSR":%d}` | ? |  |
| `climate.ventilation` | `{"ventilation":{"ventilation":%u,"ioniser":%u}}` | ? |  |

## comfort

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `comfort.ambientColour` | `{"ambientColour":{"brightnessOffset":%d,"hueAngle":%u,"hueLayer1":%u,"hueLayer2":%u,"hueLayer3":%u,"menu":%u,"mode":%u,"dimOnDrive":%u}}` | ? |  |
| `comfort.ambientLight` | `{"ambientLight":{"brightnessALEV4":%d,"brightnessLightsaber":%d,"brightnessPanoramicRoof":%d,"hueValuePanoramicRoof":%d,"modePanoramic":%u,"modeLightsaber":%u,"modeALEV4":%u,"dynamicALEV4":%u,"tcSIACharge":%u}}` | ? |  |
| `comfort.bodyTraining` | `{"bodyTraining":{"place":"RL","pressureLeft":%u,"pressureRight":%u}}`<br>`{"bodyTraining":{"place":"RR","pressureLeft":%u,"pressureRight":%u}}` | ? |  |
| `comfort.bodyTrainingStatus` |  | ? |  |
| `comfort.scentGenerator` | `{"scentGenerator":{"displayRequest":%u,"drawerState":%u,"cartridgePort":%u,"name1":%u,"name2":%u,"icon1":%u,"icon2":%u,"color1":%u,"color2":%u,"intensity":%u,"level1":%d,"level2":%d,"cartridge":%u,"temperature":%u}}` | ? |  |
| `comfort.seatControlDRR` |  | ? |  |
| `comfort.seatControlPS` |  | ? |  |
| `comfort.seatControlPSR` |  | ? |  |
| `comfort.seatLumbarRL` | `{"seatLumbarRL":%u}` | ? |  |
| `comfort.seatLumbarRR` | `{"seatLumbarRR":%u}` | ? |  |
| `comfort.seatMassageRL` | `{"seatMassageRL":{"intensity":%u,"program":%u}}` | ? |  |
| `comfort.seatMassageRR` | `{"seatMassageRR":{"intensity":%u,"program":%u}}` | ? |  |
| `comfort.seatMemory` | `{"seatMemory":{"seat":"%s","status":"%s","controller":"%s"}}` | ? |  |

## communication

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `communication.atmId` | `{"atmId":{"imei":"%s"}}` | ? |  |
| `communication.call` |  | 🚫 |  |
| `communication.callAvailability` | `{"callAvailability":{"number":"%s","callAvailabilityState":"%u"}}` | ? |  |
| `communication.callDuration0` | `{"callDuration":{"id":%u,"duration":%u}}` | ? |  |
| `communication.callDuration1` | `{"callDuration":{"id":%u,"duration":%u}}` | ? |  |
| `communication.callInfo0` | `{"callInfo":{"id":%u,"number":"%s","name":"%s"}}` | ? |  |
| `communication.callInfo1` | `{"callInfo":{"id":%u,"number":"%s","name":"%s"}}` | ? |  |
| `communication.callStatus0` | `{"callStatus":{"id":%u,"state":%u}}` | ? |  |
| `communication.callStatus1` | `{"callStatus":{"id":%u,"state":%u}}` | ? |  |
| `communication.contactDetail` | `{"contactDetail":{"id":%s,"name":"%s","surname":"%s","imageId":"%s","source":%s,"phoneNumbers":[%s],"addresses":[%s]}}` | ? |  |
| `communication.contactList` | `{"contactList":{"changed":{"numberOfEntries":%d}}}` | ? |  |
| `communication.contactPicture` | `{"contactPicture":{"id":%d}}` | ? |  |
| `communication.contactServiceProvider` | `{"contactServiceProvider":{"tagID":"%u","isServicePartner":"%d"}}` | ? |  |
| `communication.controlCall` |  | 🚫 |  |
| `communication.controlPhone` |  | 🚫 |  |
| `communication.currentCallInfo` | `{"currentCallInfo":{"name":"%s","number":"%s"}}` | ✅ arrives (personal data – left out) |  |
| `communication.gsmSIAStatus` | `{"gsmSIAStatus":{"type":%d}}` | ? |  |
| `communication.infoPlus` | `{"infoPlus":{"mailAddress":"%s"}}` | ? |  |
| `communication.lastCallInfo` | `{"lastCallInfo":{"name":"%s","number":"%s","numberType":%d}}` | ✅ arrives (personal data – left out); numberType 4, first value is garbage |  |
| `communication.phone` |  | ? |  |
| `communication.phoneStatus` | `{"phoneStatus":{"call1":%u,"call2":%u,"canMerge":%d,"canHold":%d}}` | ? |  |

## controls

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `controls.convertibleTop` | `{"convertibleTop":%d}` | ⛔ error 401 |  |
| `controls.cruiseControl` | `{"cruiseControl":{"desiredSpeed":%hu,"status":%hu}}` | ∅ |  |
| `controls.defrostRear` | `{"defrostRear":%d}` | ✅ 0 |  |
| `controls.headlights` | `{"headlights":%d}` | ✅ 0→1 |  |
| `controls.lights` | `{"lights":{"brights":%d,"parking":%d,"frontFog":%d,"rearFog":%d}}` | ✅ brights 0, parking 0→1, frontFog 0, rearFog 0 |  |
| `controls.shadowingRoof` | `{"shadowingRoof":{"errorRoofRear":%u,"statusRoofRear":%u}}` | ? |  |
| `controls.startStopLEDs` | `{"startStopLEDs":%d}` | ✅ 0/1 |  |
| `controls.startStopStatus` | `{"startStopStatus":%d}` | ✅ 128, 137, 130 |  |
| `controls.sunblind` | `{"sunblind":{"sunblindRL":%u,"sunblindRR":%u,"sunblindRW":%u}}` | ? |  |
| `controls.sunroof` | `{"sunroof":{"openPosition":%hu,"tiltPosition":%hu,"status":%d}}` | ✅ openPosition 0, tiltPosition 0, status 0 |  |
| `controls.sunroof2` | `{"sunroof2":{"posSlideCeiling":%u,"posSlideCeilingR":%u,"posSunroof":%u,"posSunroofTilt":%u,"driveSlideCeiling":%u,"driveSunroof":%u,"errorSunroofCeiling":%u,"errorSunroof":%u,"positionSlideCeiling":%u,"positionSlideCeilingTilt":%u,"positionSunroof":%u,"positionSunroofTilt":%u}}` | ? |  |
| `controls.tcProxy` | `{"tcProxy":{"NumFreeTimers":%d, IDs:[`<br>`{"tcProxy":{"senderID":"%u","eventID":"%u"}}`<br>`{"tcProxy":{"senderID":%u,"eventID":%u}}` | 🚫 |  |
| `controls.turnSignal` | `{"turnSignal":%hu}` | ✅ 0 |  |
| `controls.windowDriverFront` | `{"windowDriverFront":{"position":%hu,"status":%d,"drive":%d}}` | ✅ position 127/status 3/drive 3 (start) → 0/0/0 |  |
| `controls.windowDriverRear` | `{"windowDriverRear":{"position":%hu,"status":%d,"drive":%d}}` | ✅ like windowDriverFront |  |
| `controls.windowPassengerFront` | `{"windowPassengerFront":{"position":%hu,"status":%d,"drive":%d}}` | ✅ like windowDriverFront |  |
| `controls.windowPassengerRear` | `{"windowPassengerRear":{"position":%hu,"status":%d,"drive":%d}}` | ✅ like windowDriverFront |  |
| `controls.windshieldWiper` | `{"windshieldWiper":%d}` | ✅ 1 |  |

## driving

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `driving.acceleration` | `{"acceleration":{"lateral":%1.2f,"longitudinal":%1.2f}}` | ✅ lateral -0.36..-0.15, longitudinal -0.65..0.11 (m/s²); about 11 values/s | GaugeApp: g-meter (÷ 9.81) |
| `driving.acceleratorPedal` | `{"acceleratorPedal":{"position":%hu,"ecoPosition":%hu}}` | ✅ position 0, ecoPosition 0 (standing) |  |
| `driving.averageConsumption` | `{"averageConsumption":{"averageConsumption1":%1.1f,"averageConsumption2":%1.1f,"unit":%d}}` | ✅ averageConsumption1/2 18.9→19.0, unit 1 (l/100 km, on-board computer) |  |
| `driving.averageSpeed` | `{"averageSpeed":{"averageSpeed1":%1.1f,"averageSpeed2":%1.1f,"unit":%d}}` | ✅ averageSpeed1/2 13.8, unit 1 (km/h) |  |
| `driving.brakeContact` | `{"brakeContact":%d}` | ✅ 0, 3, 7, 16, 19, 20, 23 – graded value (pressure?), not 0/1 |  |
| `driving.clutchPedal` | `{"clutchPedal":{"position":%d}}` | ✅ position 3 (automatic) |  |
| `driving.displayRangeElectricVehicle` | `{"displayRangeElectricVehicle":%d}` | ✅ 4095 (none – not an electric car) |  |
| `driving.drivingStyle` | `{"drivingStyle":{"accelerate":%0.1f,"brake":%0.1f,"shift":%0.1f}}` | ✅ accelerate 7.5, brake 7.5, shift 7.5 |  |
| `driving.DSCActive` | `{"DSCActive":%d}` | ✅ 0 |  |
| `driving.ecoRange` | `{"ecoRange":%hu}` | ✅ 534 |  |
| `driving.ecoRangeWon` | `{"ecoRangeWon":%.1f}` | ✅ 0.0 |  |
| `driving.ecoTip` | `{"ecoTip":%d}` | ✅ 255 |  |
| `driving.electricalPowerDistribution` | `{"electricalPowerDistribution":{"rangeBoostAirConditioner":%1.2f,"rangeBoostSeatHeater":%1.2f,"power":%1.2f,"powerAirConditioner":%1.2f}}` | ✅ rangeBoostAirConditioner 409.5, rangeBoostSeatHeater 1.5, power 255 (none) |  |
| `driving.envLearning` | `{"envLearning":{"timestamp":{"s":%u,"ns":%u,"sync":%d},"version":"%u.%u.%u","qualyfier":%u,"dataBuffer":"%s"}}` | ? |  |
| `driving.FDRControl` | `{"FDRControl":%d}` | ✅ 512 / 3584 |  |
| `driving.gear` | `{"gear":%d}` | ✅ 3 (P). In D: gearbox gear + 4 (5 = D1); 1 N, 2 R, 3 P; 15 briefly while waking up | GaugeApp: gear in D = value − 4 |
| `driving.keyNumber` | `{"keyNumber":%d}` | ✅ 0 |  |
| `driving.keyPosition` | `{"keyPosition":{"terminalStatus":%d,"vehicleConditionStatus":%d,"terminalStatus30b":%d}}` | ✅ terminalStatus 10/13, vehicleConditionStatus 5/7/11, terminalStatus30b 13 |  |
| `driving.laneBoundaries` |  | ? |  |
| `driving.laneBoundariesLoFrq` |  | ? |  |
| `driving.laneChange` |  | ? |  |
| `driving.mode` | `{"mode":%d}` | ⛔ error 401 | no driving mode (Sport/Comfort) |
| `driving.mode35up` |  | ? |  |
| `driving.odometer` | `{"odometer":%lu}` | ✅ km (total mileage) |  |
| `driving.orInfo` | `{"orInfo":%d}` | ? |  |
| `driving.orNPITextMessage` | `{"orNPITextMessage":%d}` | ? |  |
| `driving.parkingBrake` | `{"parkingBrake":%d}` | ✅ 0 |  |
| `driving.rsConfigStatus` | `{"rsConfigStatus":{"CountryCodingSpeedSigns":%d,"UnitSpeedLimit":%d}}` | ? |  |
| `driving.shiftIndicator` | `{"shiftIndicator":%d}` | ✅ 0 |  |
| `driving.signRecognitionFrontCamera` |  | ? |  |
| `driving.sliActualSpeedLimitInfo` | `{"sliActualSpeedLimitInfo":{"actualClearingSpeedLimit":%d,"actualSpeedLimit":%d}}` | ? |  |
| `driving.sliNextSpeedLimitRecognition` | `{"sliNextSpeedLimitRecognition":{"nextClearingSpeedLimit":%d,"nextSpeedLimit":%d}}` | ? |  |
| `driving.sliTextMessage` | `{"sliTextMessage":%d}` | ? |  |
| `driving.SOCHoldState` |  | ⛔ error 400 |  |
| `driving.speedActual` | `{"speedActual":%hu}` | ✅ 0 (standing) – km/h, whole numbers |  |
| `driving.speedDisplayed` | `{"speedDisplayed":%hu}` | ✅ 0 |  |
| `driving.steeringWheel` | `{"steeringWheel":{"angle":%1.1f,"speed":%1.1f,"error":%d}}` | ✅ angle -3.9 (°), speed 65535 (none), error 0 |  |
| `driving.trafficSignInfo1` | `{"trafficSignInfo1":{"trafficSignInformation1":%d,"trafficSignPosition1":%d,"trafficSignPositionVariable1":%d,"trafficSignEnvironment1":%d}}` | ? |  |
| `driving.trafficSignInfo2` | `{"trafficSignInfo2":{"trafficSignInformation2":%d,"trafficSignPosition2":%d,"trafficSignPositionVariable2":%d,"trafficSignEnvironment2":%d}}` | ? |  |
| `driving.trafficSignInfo3` | `{"trafficSignInfo3":{"trafficSignInformation3":%d,"trafficSignPosition3":%d,"trafficSignPositionVariable3":%d,"trafficSignEnvironment3":%d}}` | ? |  |
| `driving.trafficSignInfo4` | `{"trafficSignInfo4":{"trafficSignInformation4":%d,"trafficSignPosition4":%d,"trafficSignPositionVariable4":%d,"trafficSignEnvironment4":%d}}` | ? |  |
| `driving.trafficSignInfoVisibility` | `{"trafficSignInfoVisibility":%d}` | ? |  |

## engine

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `engine.consumption` | `{"consumption":%hu}` | ✅ 0 → 30119 in about 55 s, only grows: injected fuel counter (%hu, wraps at 65536), unit unknown | GaugeApp: instant consumption, calibrated from the tank |
| `engine.electricVehicleMode` | `{"electricVehicleMode":%d}` | ✅ 15 |  |
| `engine.info` | `{"info":{"numberOfGears":%d,"numberOfCylinders":%d,"fuelType":%d,"gearboxType":%d,"displacement":%hu}}` | ✅ first 15/15/15/15/25500 (none), after 14 s: numberOfGears 8, numberOfCylinders 4, fuelType 4, gearboxType 1, displacement 2000 |  |
| `engine.rangeCalc` | `{"rangeCalc":{"energyREXGenerator":%u,"energyEMotorTraction":%u,"energyEMotorRecuperation":%u,"auxConsumerEnergy":%u,"auxConsumerEnergyBaseLoad":%u}}` | ∅ |  |
| `engine.RPMSpeed` | `{"RPMSpeed":%hu}` | ✅ 0..1929 (1/min); about 2.3 values/s |  |
| `engine.status` | `{"status":%d}` | ✅ 0 → 1 → 2 (off / starting / running?) |  |
| `engine.temperature` | `{"temperature":{"engine":%d,"oil":%d}}` | ✅ engine 7, oil 6 (°C, cold engine; changes in 1 °C steps) |  |
| `engine.torque` | `{"torque":%hd}` | ✅ -39..134 (Nm, negative on engine braking) | GaugeApp: torque, power = Nm × rpm / 7023.5 |

## entertainment

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `entertainment.descriptionCurrentSource` | `{"descriptionCurrentSource":{"sourceName":"%s"}}` | ? |  |
| `entertainment.drive.blurayMemory` | `{"blurayMemory":%u}` | ? |  |
| `entertainment.drive.chapterList` | `{"chapterList":{"chapterID":%d,"chapterCount":%d}}` | ? |  |
| `entertainment.drive.colorButtonColorList` |  | ? |  |
| `entertainment.drive.controlCurrentSource` |  | 🚫 |  |
| `entertainment.drive.controlPlayback` |  | 🚫 |  |
| `entertainment.drive.coverArt` | `{"coverArt":{"sourceName":"%s","coverArt":"%s"}}` | ? |  |
| `entertainment.drive.language` | `{"language":%d}` | ? |  |
| `entertainment.drive.mediabrowsing` | `{"mediabrowsing":{"sourceName":"%s","startIndex":%s,"windowSize":%s,"totalNumber":%s,"items":[%s]}}` | ? |  |
| `entertainment.drive.pipSuppress` | `{"pipSuppress":{"sourceName":"%s","pipSuppressed":%s}}` | ? |  |
| `entertainment.drive.playList` | `{"playList":{"sourceName":"%s","objID":%s,"index":%s,"endObjID":%s,"endIndex":%s,"reason":%s}}`<br>`{"playList":{"sourceName":"%s","parentObjID":"%s","reason":%s}}`<br>`{"playList":{"sourceName":"%s","startObjID":%d,"startIndex":%d,"selectedObjID":%d,"selectedIndex":%d,"length":%u,"totalLength":%s,"playList":[%s]}}` | ? |  |
| `entertainment.drive.random` | `{"random":{"sourceName":"%s","random":%s}}` | ? |  |
| `entertainment.drive.statusCurrentSource` | `{"statusCurrentSource":{"sourceName":"%s","mediaInfo":"%s","playBackState":"%s","trackID":%s,"objID":"%s","currentChapter":%s}}` | ? |  |
| `entertainment.drive.statusMetaInfo` | `{"statusMetaInfo":{"sourceName":"%s","title":"%s","album":"%s","artist":"%s","albumObjID":"%s","artistObjID":"%s","genre":"%s","stationName":"%s"}}` | ? |  |
| `entertainment.drive.statusPlayback` | `{"statusPlayback":{"sourceName":"%s","trackTimePosition":%s,"totalTrackTime":%s}}` | ? |  |
| `entertainment.drive.subtitle` |  | ? |  |
| `entertainment.drive.videoAngle` |  | ? |  |
| `entertainment.md.browsingCapabilities` | `{"browsingCapabilities":{"sourceName":"%s","directory":%s,"musicSearch":%s,"playlist":%s,"video":%s,"audiobook":%s,"podcast":%s,"currentPlaylist":%s}}` | ? |  |
| `entertainment.md.controlPlayback` |  | 🚫 |  |
| `entertainment.md.coverArt` | `{"coverArt":{"sourceName":"%s","coverArt":"%s"}}` | ? |  |
| `entertainment.md.mediabrowsing` | `{"mediabrowsing":{"sourceName":"%s","startIndex":%s,"windowSize":%s,"totalNumber":%s,"items":[%s]}}` | ? |  |
| `entertainment.md.playingCapabilities` | `{"playingCapabilities":{"sourceName":"%s","AVRCP":"%s","playable":%s,"trackPosition":%s,"timeInfo":%s,"playList":%s}}` | ? |  |
| `entertainment.md.playList` | `{"playList":{"sourceName":"%s","objID":%s,"index":%s,"endObjID":%s,"endIndex":%s,"reason":%s}}`<br>`{"playList":{"sourceName":"%s","parentObjID":"%s","reason":%s}}`<br>`{"playList":{"sourceName":"%s","startObjID":%d,"startIndex":%d,"selectedObjID":%d,"selectedIndex":%d,"length":%u,"totalLength":%s,"playList":[%s]}}` | ? |  |
| `entertainment.md.random` | `{"random":{"sourceName":"%s","random":%s}}` | ? |  |
| `entertainment.md.statusCurrentSource` | `{"statusCurrentSource":{"sourceName":"%s","mediaInfo":"%s","playBackState":"%s","trackID":%s,"objID":"%s","currentChapter":%s}}` | ? |  |
| `entertainment.md.statusMetaInfo` | `{"statusMetaInfo":{"sourceName":"%s","title":"%s","album":"%s","artist":"%s","albumObjID":"%s","artistObjID":"%s","genre":"%s","stationName":"%s"}}` | ? |  |
| `entertainment.md.statusPlayback` | `{"statusPlayback":{"sourceName":"%s","trackTimePosition":%s,"totalTrackTime":%s}}` | ? |  |
| `entertainment.mediabrowsing` | `{"mediabrowsing":{"sourceName":"%s","startIndex":%s,"windowSize":%s,"totalNumber":%s,"items":[%s]}}` | ? |  |
| `entertainment.multimedia` | `{"multimedia":{"title":"%s","artist":"%s","album":"%s","source":%d}}` | ✅ title/artist/album (text), source 0→34 |  |
| `entertainment.radioFrequency` | `{"radioFrequency":%u}` | ✅ 103600 (kHz) |  |
| `entertainment.radioStation` | `{"radioStation":{"frequency":%u,"name":"%s","HDMode":%d,"HDChannel":%d,"nameInfo":%d}}` | ✅ frequency, name, HDMode 0, HDChannel 0, nameInfo 0 |  |
| `entertainment.rhmi.coverArt` | `{"coverArt":{"sourceName":"%s","coverArt":"%s"}}` | ? |  |
| `entertainment.rhmi.providerLogo` |  | ? |  |
| `entertainment.rhmi.statusCurrentSource` | `{"statusCurrentSource":{"sourceName":"%s","mediaInfo":"%s","playBackState":"%s","trackID":%s,"objID":"%s","currentChapter":%s}}` | ? |  |
| `entertainment.rhmi.statusMetaInfo` | `{"statusMetaInfo":{"sourceName":"%s","title":"%s","album":"%s","artist":"%s","albumObjID":"%s","artistObjID":"%s","genre":"%s","stationName":"%s"}}` | ? |  |
| `entertainment.statusAllowedSources` | `{"statusAllowedSources":{"availableSources":[%s],"allowed":[%s],"removable":[%s]}}` | ? |  |
| `entertainment.statusAvailableSources` | `{"statusAvailableSources":{"activeSource":"%s","availableSources":[%s],"removable":[%s]}}` | ? |  |
| `entertainment.tuner.coverArt` | `{"coverArt":{"sourceName":"%s","coverArt":"%s"}}` | ? |  |
| `entertainment.tuner.epgEvent` | `{"epgEvent":{"sourceName":"%s","eventName":"%s","startHour":%s,"startMinute":%s,"endHour":%s,"endMinute":%s}}` | ? |  |
| `entertainment.tuner.info` | `{"info":{"sourceName":"%s","info":"%s"}}` | ? |  |
| `entertainment.tuner.playList` | `{"playList":{"sourceName":"%s","objID":%s,"index":%s,"endObjID":%s,"endIndex":%s,"reason":%s}}`<br>`{"playList":{"sourceName":"%s","parentObjID":"%s","reason":%s}}`<br>`{"playList":{"sourceName":"%s","startObjID":%d,"startIndex":%d,"selectedObjID":%d,"selectedIndex":%d,"length":%u,"totalLength":%s,"playList":[%s]}}` | ? |  |
| `entertainment.tuner.signalQuality` | `{"signalQuality":{"sourceName":"%s","TV":%s}}` | ? |  |
| `entertainment.tuner.statusCurrentSource` | `{"statusCurrentSource":{"sourceName":"%s","mediaInfo":"%s","playBackState":"%s","trackID":%s,"objID":"%s","currentChapter":%s}}` | ? |  |
| `entertainment.tuner.statusMetaInfo` | `{"statusMetaInfo":{"sourceName":"%s","title":"%s","album":"%s","artist":"%s","albumObjID":"%s","artistObjID":"%s","genre":"%s","stationName":"%s"}}` | ? |  |
| `entertainment.tuner.statusPlayback` | `{"statusPlayback":{"sourceName":"%s","trackTimePosition":%s,"totalTrackTime":%s}}` | ? |  |
| `entertainment.video.controlCurrentSource` |  | 🚫 |  |
| `entertainment.video.epgEvent` | `{"epgEvent":{"sourceName":"%s","eventName":"%s","startHour":%s,"startMinute":%s,"endHour":%s,"endMinute":%s}}` | ? |  |
| `entertainment.video.language` | `{"language":%d}` | ? |  |
| `entertainment.video.playList` | `{"playList":{"sourceName":"%s","objID":%s,"index":%s,"endObjID":%s,"endIndex":%s,"reason":%s}}`<br>`{"playList":{"sourceName":"%s","parentObjID":"%s","reason":%s}}`<br>`{"playList":{"sourceName":"%s","startObjID":%d,"startIndex":%d,"selectedObjID":%d,"selectedIndex":%d,"length":%u,"totalLength":%s,"playList":[%s]}}` | ? |  |
| `entertainment.video.signalQuality` | `{"signalQuality":{"sourceName":"%s","TV":%s}}` | ? |  |
| `entertainment.video.stationScan` | `{"stationScan":{"isScanActive":%d,"scanProgress":%d}}` | ? |  |
| `entertainment.video.statusCurrentSource` | `{"statusCurrentSource":{"sourceName":"%s","mediaInfo":"%s","playBackState":"%s","trackID":%s,"objID":"%s","currentChapter":%s}}` | ? |  |
| `entertainment.video.statusMetaInfo` | `{"statusMetaInfo":{"sourceName":"%s","title":"%s","album":"%s","artist":"%s","albumObjID":"%s","artistObjID":"%s","genre":"%s","stationName":"%s"}}` | ? |  |
| `entertainment.video.statusPlayback` | `{"statusPlayback":{"sourceName":"%s","trackTimePosition":%s,"totalTrackTime":%s}}` | ? |  |
| `entertainment.video.subtitle` |  | ? |  |
| `entertainment.video.teletext` | `{"teletext":{"sourceName":"%s","currentPage":%s,"available":%s}}` | ? |  |

## hmi

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `hmi.displayControl` | `{"displayControl":{"enabled":%u,"brightness":%d}}` | ? |  |
| `hmi.graphicalContext` | `{"graphicalContext":{"visibleContext":%d,"focusIndex":%u,"listIndex":%d,"widgetType":"%s","enabled":"%d","selected":"%d","menuTitle":"%s","appType":"%d","shiftDirections":"%s","scrollDirection":"%s"}}` | ✅ visibleContext, focusIndex, listIndex, widgetType, menuTitle = title of the state on screen (e.g. "CDS SCAN") | GaugeApp: which screen is visible |
| `hmi.httpTransfer` | `{"httpTransfer":{"AppCode":%d,"CABID":%d}}`<br>`{"httpTransfer":{"CABID":%d,"filePath":"%s"}}`<br>`{"httpTransfer":{"command":"%s","dataBuffer":"%s"}}`<br>`{"httpTransfer":{"command":"%s"}}` | 🚫 |  |
| `hmi.iDrive` | `{"iDrive":{"instance":%u,"command":%u,"value":%d}}` | 🚫 | controller input (instance/command/value); no answer in the 0.1 scan |
| `hmi.seeAllInfo` | `{"seeAllInfo":{"seeAll":%d,"previousPossible":%d,"nextPossible":%d}}` | ? |  |
| `hmi.speedlock` | `{"speedlock":"%s"}` | ? |  |
| `hmi.spellerInput` | `{"spellerInput":{"stateid":"%s","info":"%s","type":"%s","usecase":"%s","input":"%s","passwordMode":"%s"}}` | 🚫 |  |
| `hmi.statistic` | `{"statistic":{"cat":%d,"categoryDesc":"%s","counter":%d,"counterDesc":"%s","data":%s}}`<br>`{"statistic":{"cat":%d,"categoryDesc":"%s","counter":%d,"counterDesc":"%s","type":"%s"}}`<br>`{"statistic":{"cat":%d,"categoryDesc":"%s","counter":%d,"data":"{"appstateid":%u,"entity":%u,"speechmode":%u}"}}`<br>`{"statistic":{"cat":%d,"counter":%d,"data":"{"appstateid":%u,"entity":%u,"speechmode":%u}"}}`<br>`{"statistic":{"cat":%d,"counter":%d,"data":%s}}`<br>`{"statistic":{"cat":%d,"counter":%d,"type":"%s"}}` | ? |  |
| `hmi.tts` |  | ∅ |  |
| `hmi.videolock` | `{"videolock":"%s"}` | ? |  |

## mmi

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `mmi.rseAccess` | `{"rseAccess":{"RSEAccessLock":%d}}` | ? |  |

## navigation

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `navigation.currentPositionCountry` | `{"currentPositionCountry":"%s"}` | ? |  |
| `navigation.currentPositionDetailedInfo` | `{"currentPositionDetailedInfo":{"street":"%s","houseNumber":"%s","crossStreet":"%s","city":"%s","country":"%s"}}` | ✅ arrives (personal data – left out) |  |
| `navigation.finalDestination` | `{"finalDestination":{"latitude":%f,"longitude":%f}}` | ∅ |  |
| `navigation.finalDestinationDetailedInfo` | `{"finalDestinationDetailedInfo":{"street":"%s","houseNumber":"%s","crossStreet":"%s","city":"%s","country":"%s"}}` | ✅ empty (no route) |  |
| `navigation.getCABUrl` | `{"getCABUrl":{"CABID":%u,"URL":"%s"}}` | 🚫 |  |
| `navigation.GPSExtendedInfo` | `{"GPSExtendedInfo":{"altitude":%d,"heading":%.4f,"quality":%d,"speed":%d}}` | ✅ altitude, heading, quality (−32768/32767 = none at the start); speed always −32768 |  |
| `navigation.GPSPosition` | `{"GPSPosition":{"latitude":%f,"longitude":%f}}` | ✅ arrives (personal data – left out); −596.52 / 0.0 at the start = none |  |
| `navigation.GPSRawData` | `{"GPSRawData":{"latitude":%f,"longitude":%f,"height":%d,"heading":%f,"speed":%f,"fix":%d}}` | ? |  |
| `navigation.guidanceStatus` | `{"guidanceStatus":%hu}` | ✅ 0 |  |
| `navigation.infoToFinalDestination` | `{"infoToFinalDestination":{"airDistance":%1.3f,"direction":%hu,"distance":%1.3f,"remainingTime":%hd,"routeHandle":%hu}}` | ✅ all zeros (no route) |  |
| `navigation.infoToNextDestination` | `{"infoToNextDestination":{"airDistance":%1.3f,"direction":%hu,"distance":%1.3f,"remainingTime":%hd,"routeHandle":%hu}}` | ✅ all zeros (no route) |  |
| `navigation.mapFeature` |  | ? |  |
| `navigation.naviguidanceinfo` | `{"naviGuidanceInfo":{"distance":"%s","distanceUnit":"%s","arrivalTime":"%s"}}` | ? |  |
| `navigation.nextDestination` | `{"nextDestination":{"name":"%s","type":%d,"latitude":%f,"longitude":%f}}` | ✅ empty |  |
| `navigation.nextDestinationDetailedInfo` | `{"nextDestinationDetailedInfo":{"street":"%s","houseNumber":"%s","crossStreet":"%s","city":"%s","country":"%s"}}` | ✅ empty |  |
| `navigation.onlineAppInformation` |  | ? |  |
| `navigation.onlineStartUseCase.CountryInformation` |  | ? |  |
| `navigation.onlineStartUseCase.IntermodalInformation` |  | ? |  |
| `navigation.onlineStartUseCase.IntermodalRouteChange` |  | ? |  |
| `navigation.onlineStartUseCase.IntermodalRouteInfo` |  | ? |  |
| `navigation.onlineStartUseCase.OnlineSearch` |  | ? |  |
| `navigation.onlineStartUseCase.PictureOnDestination` |  | ? |  |
| `navigation.onlineStartUseCase.POIEnrichment` |  | ? |  |
| `navigation.onlineStartUseCase.RouteInfoUploadBrowser` |  | ? |  |
| `navigation.onlineStartUseCase.TripChoiceHMI` |  | ? |  |
| `navigation.poiCategorySearch` |  | ? |  |
| `navigation.requestJourneys` |  | 🚫 |  |
| `navigation.routeElapsedInfo` | `{"routeElapsedInfo":{"distance":%u,"time":%hu}}` | ✅ distance 0, time 0 |  |
| `navigation.showDestination` |  | 🚫 |  |
| `navigation.triplist` |  | ? |  |
| `navigation.units` | `{"units":%d}`<br>`{"units":{"language":%d,"time":%d,"consumption":%d,"fuel":%d,"distance":%d,"airPressure":%d,"speedometerDigital":%d,"sportPower":%d,"sportTorque":%d,"electricConsumption":%d,"date":%d,"temperature":%d}}` | ✅ 1→2 |  |

## sensors

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `sensors.battery` | `{"battery":%hu}` | ✅ 255 (start) → 96..97 (battery %?) |  |
| `sensors.batteryTemp` | `{"batteryTemp":%d}` | ✅ 255 (none) |  |
| `sensors.childSafetyLock` | `{"childSafetyLock":%u}` | ? |  |
| `sensors.doors` | `{"doors":{"driver":%hu,"passenger":%hu,"driverRear":%hu,"passengerRear":%hu}}` | ✅ driver/passenger/driverRear/passengerRear 0 |  |
| `sensors.fuel` | `{"fuel":{"range":%hu,"reserve":%d,"tanklevel":%hu}}` | ✅ range 498 (km), reserve 0, tanklevel 37 (l) |  |
| `sensors.lid` | `{"lid":%d}` | ✅ 1 |  |
| `sensors.PDCRangeFront` | `{"PDCRangeFront":{"outLeft":%d,"left":%d,"middleLeft":%d,"middleRight":%d,"right":%d,"outRight":%d}}` | ∅ | only the "2" version works |
| `sensors.PDCRangeFront2` | `{"PDCRangeFront2":{"left1":%d,"left2":%d,"left3":%d,"left4":%d,"right4":%d,"right3":%d,"right2":%d,"right1":%d}}` | ✅ 8 sensors (left1..4, right4..1), 253 = no obstacle; about 1 value/s while manoeuvring |  |
| `sensors.PDCRangeRear` | `{"PDCRangeRear":{"outLeft":%d,"left":%d,"middleLeft":%d,"middleRight":%d,"right":%d,"outRight":%d}}` | ∅ | only the "2" version works |
| `sensors.PDCRangeRear2` | `{"PDCRangeRear2":{"left1":%d,"left2":%d,"left3":%d,"left4":%d,"right4":%d,"right3":%d,"right2":%d,"right1":%d}}` | ✅ like PDCRangeFront2 |  |
| `sensors.PDCStatus` | `{"PDCStatus":%d}` | ✅ 2 |  |
| `sensors.seatbelt` | `{"seatbelt":{"driverFront":%d,"passengerFront":%d,"driverRear":%d,"passengerRear":%d,"centerRear":%d}}` | ✅ driverFront, passengerFront, driverRear, passengerRear, centerRear 0 |  |
| `sensors.seatOccupiedDriver` | `{"seatOccupiedDriver":%d}` | ✅ 4 |  |
| `sensors.seatOccupiedPassenger` | `{"seatOccupiedPassenger":%d}` | ✅ 0 / 7 |  |
| `sensors.seatOccupiedRearLeft` | `{"seatOccupiedRearLeft":%d}` | ✅ 4 |  |
| `sensors.seatOccupiedRearRight` | `{"seatOccupiedRearRight":%d}` | ✅ 4 |  |
| `sensors.SOCBatteryHybrid` | `{"SOCBatteryHybrid":%1.2f}` | ✅ 255.00 (none) |  |
| `sensors.temperatureExterior` | `{"temperatureExterior":%1.1f}` | ✅ 5.0 (°C) |  |
| `sensors.temperatureInterior` | `{"temperatureInterior":%1.1f}` | ✅ 10.0..10.8 (°C, 0.1 steps) |  |
| `sensors.tirePressureWarning` | `{"tirePressureWarning":{"status":%d}}` | ? |  |
| `sensors.trunk` | `{"trunk":%d}` | ✅ 0 |  |

## specialvehicle

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `specialvehicle.menucontrol` |  | ? |  |

## vehicle

| Name | Format (libhmiremoting.so) | F40 scan | Notes |
|---|---|---|---|
| `vehicle.country` | `{"country":%d}` | ✅ 255 → 2 |  |
| `vehicle.dayNightChangeOver` | `{"dayNightChangeOver":%u}` | ? |  |
| `vehicle.fasStatus` | `{"fasStatus":{"breakassistentTresholdStatus":%d,"collisionWarning":%d,                                                    "laneChangeWarning":%d,"laneDepartureWarning":%d,"personWarning":%d,                                                    "selectiveSpotlight":%d,"displayPanel":%d,"speedAssistant":%d,"speedOffset":%d}}` | ? |  |
| `vehicle.fastCharging` | `{"fastCharging":"%s"}` | ? |  |
| `vehicle.interactionDetection` |  | ? |  |
| `vehicle.language` | `{"language":%d}` | ✅ 18 (Polish); 3 = EN_US |  |
| `vehicle.partialNetworkRequest` | `{"partialNetworkRequest":{"errorCode":%d,"errorText":"Car is in PWF status PARKING"}}` | ? |  |
| `vehicle.partType` | `{"partType":{"typeBody":%d,"quantityCylinder":%d,"quantityGear":%d,                                                    "typeEngine":%d,"typeSteering":%d,"typeGearbox":%d,"typeCapacity":%d}}` | ? |  |
| `vehicle.powerStateHeadUnit` | `{"powerStateHeadUnit":"%s"}`<br>`{"powerStateHeadUnit":%u}` | ? |  |
| `vehicle.statePWF` | `{"statePWF":%d}` | ? |  |
| `vehicle.systemTime` | `{"systemTime":%lu}` | ✅ seconds, every 1 s |  |
| `vehicle.time` | `{"time":{"hour":%hu,"minute":%hu,"second":%hu,"date":%hu,"month":%hu,"weekday":%d,"year":%hu}}` | ✅ hour, minute, second (every 5 s), date, month, weekday, year |  |
| `vehicle.type` | `{"type":"%s","objID":"%s"}`<br>`{"type":"%s","street":"%s","number":"%s","city":"%s","zip":"%s"}`<br>`{"type":%d}`<br>`{"type":%u, "available":%u, "checked":%u}` | ✅ 255 → 132 |  |
| `vehicle.units` | `{"units":%d}`<br>`{"units":{"language":%d,"time":%d,"consumption":%d,"fuel":%d,"distance":%d,"airPressure":%d,"speedometerDigital":%d,"sportPower":%d,"sportTorque":%d,"electricConsumption":%d,"date":%d,"temperature":%d}}` | ✅ language 18, time 2, consumption 1, fuel 1, distance 1, airPressure 1, speedometerDigital 0, sportPower 1, sportTorque 1, electricConsumption 1, date 1, temperature 1 | the car's unit settings |
| `vehicle.unitSpeed` | `{"unitSpeed":%d}` | ✅ 0 |  |
| `vehicle.userTimeZone` | `{"userTimeZone":{"timeZoneID":%u,"timeZoneHour":%d,"timeZoneMinute":%u}}` | ? |  |
| `vehicle.VIN` | `{"VIN":"%s"}` | ✅ arrives (personal data – left out) |  |

Summary: 93 with data, 3 with an error, 7 without an answer, 145 not scanned, 15 left out.
