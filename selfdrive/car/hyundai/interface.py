from cereal import car
from common.numpy_fast import interp
from panda import Panda
from openpilot.common.conversions import Conversions as CV
from openpilot.selfdrive.car.hyundai.hyundaicanfd import CanBus
from openpilot.selfdrive.car.hyundai.values import HyundaiFlags, CAR, DBC, CANFD_CAR, CAMERA_SCC_CAR, CANFD_RADAR_SCC_CAR, \
                                         CANFD_UNSUPPORTED_LONGITUDINAL_CAR, EV_CAR, HYBRID_CAR, LEGACY_SAFETY_MODE_CAR, \
                                         UNSUPPORTED_LONGITUDINAL_CAR, Buttons
from openpilot.selfdrive.car.hyundai.radar_interface import RADAR_START_ADDR
from openpilot.selfdrive.car import create_button_events, get_safety_config
from openpilot.selfdrive.car.interfaces import CarInterfaceBase, ACCEL_MIN, ACCEL_MAX
from openpilot.selfdrive.car.disable_ecu import disable_ecu
from openpilot.selfdrive.controls.neokii.cruise_state_manager import is_radar_point
from openpilot.common.params import Params

Ecu = car.CarParams.Ecu
ButtonType = car.CarState.ButtonEvent.Type
EventName = car.CarEvent.EventName
ENABLE_BUTTONS = (Buttons.RES_ACCEL, Buttons.SET_DECEL, Buttons.CANCEL)
BUTTONS_DICT = {Buttons.RES_ACCEL: ButtonType.accelCruise, Buttons.SET_DECEL: ButtonType.decelCruise,
                Buttons.GAP_DIST: ButtonType.gapAdjustCruise, Buttons.CANCEL: ButtonType.cancel}


class CarInterface(CarInterfaceBase):
  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    v_current_kph = current_speed * CV.MS_TO_KPH
    gas_max_bp = [7., 15., 30., 70., 130., 150.]
    gas_max_v = [2.0, 1.3, 0.8, 0.4, 0.15, 0.1]
    return ACCEL_MIN, interp(v_current_kph, gas_max_bp, gas_max_v)

  @staticmethod
  def _get_params(ret, candidate, fingerprint, car_fw, experimental_long, docs):
    ret.carName = "hyundai"
    ret.radarUnavailable = RADAR_START_ADDR not in fingerprint[1] or DBC[ret.carFingerprint]["radar"] is None

    # These cars have been put into dashcam only due to both a lack of users and test coverage.
    # These cars likely still work fine. Once a user confirms each car works and a test route is
    # added to selfdrive/car/tests/routes.py, we can remove it from this list.
    # FIXME: the Optima Hybrid 2017 uses a different SCC12 checksum
    ret.dashcamOnly = candidate in {CAR.KIA_OPTIMA_H, }

    hda2 = Ecu.adas in [fw.ecu for fw in car_fw] or candidate == CAR.GENESIS_GV80_MR_MOON
    CAN = CanBus(None, hda2, fingerprint)

    if candidate in CANFD_CAR:
      # detect if car is hybrid
      if 0x105 in fingerprint[CAN.ECAN]:
        ret.flags |= HyundaiFlags.HYBRID.value
      elif candidate in EV_CAR:
        ret.flags |= HyundaiFlags.EV.value

      # detect HDA2 with ADAS Driving ECU
      if hda2:
        ret.flags |= HyundaiFlags.CANFD_HDA2.value
        if 0x110 in fingerprint[CAN.CAM]:
          ret.flags |= HyundaiFlags.CANFD_HDA2_ALT_STEERING.value
        if candidate == CAR.GENESIS_GV80_MR_MOON:
          ret.flags |= HyundaiFlags.CANFD_ALT_GEARS.value
      else:
        # non-HDA2
        if 0x1cf not in fingerprint[CAN.ECAN]:
          ret.flags |= HyundaiFlags.CANFD_ALT_BUTTONS.value
        # ICE cars do not have 0x130; GEARS message on 0x40 or 0x70 instead
        if 0x130 not in fingerprint[CAN.ECAN]:
          if 0x40 not in fingerprint[CAN.ECAN]:
            ret.flags |= HyundaiFlags.CANFD_ALT_GEARS_2.value
          else:
            ret.flags |= HyundaiFlags.CANFD_ALT_GEARS.value
        if candidate not in CANFD_RADAR_SCC_CAR:
          ret.flags |= HyundaiFlags.CANFD_CAMERA_SCC.value
    else:
      # TODO: detect EV and hybrid
      if candidate in HYBRID_CAR:
        ret.flags |= HyundaiFlags.HYBRID.value
      elif candidate in EV_CAR:
        ret.flags |= HyundaiFlags.EV.value

      # Send LFA message on cars with HDA
      if 0x485 in fingerprint[2]:
        ret.flags |= HyundaiFlags.SEND_LFA.value

      # These cars use the FCA11 message for the AEB and FCW signals, all others use SCC12
      if 0x38d in fingerprint[0] or 0x38d in fingerprint[2]:
        ret.flags |= HyundaiFlags.USE_FCA.value

    ret.steerActuatorDelay = 0.2  # Default delay
    ret.steerLimitTimer = 0.4
    CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    # *** longitudinal control ***
    if candidate in CANFD_CAR:
      ret.longitudinalTuning.kpBP = [0., 10.]
      ret.longitudinalTuning.kpV = [0.5, 0.2]
      ret.longitudinalTuning.kiV = [0.0]
      ret.experimentalLongitudinalAvailable = candidate not in CANFD_UNSUPPORTED_LONGITUDINAL_CAR
    else:
      ret.longitudinalTuning.kpBP = [0., 10.]
      ret.longitudinalTuning.kpV = [1.2, 0.6]
      ret.longitudinalTuning.kiV = [0.0]
      ret.experimentalLongitudinalAvailable = True #candidate not in (LEGACY_SAFETY_MODE_CAR)

    ret.openpilotLongitudinalControl = experimental_long and ret.experimentalLongitudinalAvailable
    ret.pcmCruise = not ret.openpilotLongitudinalControl

    ret.stoppingControl = True
    ret.startingState = False
    ret.stoppingDecelRate = 0.3
    ret.steerActuatorDelay = 0.2
    ret.steerLimitTimer = 2.0

    ret.vEgoStarting = 0.1
    ret.vEgoStopping = 0.1
    ret.startAccel = 1.0
    #ret.longitudinalActuatorDelayLowerBound = 0.5
    #ret.longitudinalActuatorDelayUpperBound = 0.5
    ret.radarTimeStep = 0.02  # 50hz

    # *** feature detection ***
    if candidate in CANFD_CAR:
      ret.enableBsm = 0x1e5 in fingerprint[CAN.ECAN]
    else:
      ret.enableBsm = 0x58b in fingerprint[0]

    # *** panda safety config ***
    if candidate in CANFD_CAR:
      cfgs = [get_safety_config(car.CarParams.SafetyModel.hyundaiCanfd), ]
      if CAN.ECAN >= 4:
        cfgs.insert(0, get_safety_config(car.CarParams.SafetyModel.noOutput))
      ret.safetyConfigs = cfgs

      if ret.flags & HyundaiFlags.CANFD_HDA2:
        ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_CANFD_HDA2
        if ret.flags & HyundaiFlags.CANFD_HDA2_ALT_STEERING:
          ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_CANFD_HDA2_ALT_STEERING
      if ret.flags & HyundaiFlags.CANFD_ALT_BUTTONS:
        ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_CANFD_ALT_BUTTONS
      if ret.flags & HyundaiFlags.CANFD_CAMERA_SCC:
        ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_CAMERA_SCC

      ret.sccBus = 0
    else:
      if candidate in LEGACY_SAFETY_MODE_CAR:
        # these cars require a special panda safety mode due to missing counters and checksums in the messages
        ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.hyundaiLegacy)]
      else:
        ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.hyundai, 0)]

      ret.sccBus = 2 if (candidate in CAMERA_SCC_CAR or Params().get_bool('SccOnBus2')) else 0
      ret.hasAutoHold = 1151 in fingerprint[0]
      ret.hasLfaHda = 1157 in fingerprint[0]
      ret.hasNav = 1348 in fingerprint[0]

      if not ret.openpilotLongitudinalControl:
        ret.radarUnavailable = ret.sccBus == -1

      if ret.sccBus == 2:
        ret.hasScc13 = 1290 in fingerprint[0] or 1290 in fingerprint[2]
        ret.hasScc14 = 905 in fingerprint[0] or 905 in fingerprint[2]
        ret.openpilotLongitudinalControl = True
        ret.radarUnavailable = False
        ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.hyundaiLegacy)]

    if ret.openpilotLongitudinalControl and ret.sccBus == 0 and not Params().get_bool('CruiseStateControl'):
      ret.pcmCruise = False
    else:
      ret.pcmCruise = True # managed by cruise state manager

    if ret.openpilotLongitudinalControl:
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_LONG
    if ret.flags & HyundaiFlags.HYBRID:
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_HYBRID_GAS
    elif ret.flags & HyundaiFlags.EV:
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_EV_GAS

    if candidate in (CAR.KONA, CAR.KONA_EV, CAR.KONA_HEV, CAR.KONA_EV_2022):
      ret.flags |= HyundaiFlags.ALT_LIMITS.value
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_HYUNDAI_ALT_LIMITS

    if ret.centerToFront == 0:
      ret.centerToFront = ret.wheelbase * 0.4

    return ret

  @staticmethod
  def init(CP, logcan, sendcan):
    if is_radar_point(CP) and not (CP.flags & HyundaiFlags.CANFD_CAMERA_SCC.value):
      addr, bus = 0x7d0, 0
      if CP.flags & HyundaiFlags.CANFD_HDA2.value:
        addr, bus = 0x730, CanBus(CP).ECAN
      disable_ecu(logcan, sendcan, bus=bus, addr=addr, com_cont_req=b'\x28\x83\x01')

    # for blinkers
    if CP.flags & HyundaiFlags.ENABLE_BLINKERS:
      disable_ecu(logcan, sendcan, bus=CanBus(CP).ECAN, addr=0x7B1, com_cont_req=b'\x28\x83\x01')

  def _update(self, c):
    ret = self.CS.update(self.cp, self.cp_cam)

    if self.CS.cruise_buttons[-1] != self.CS.prev_cruise_buttons:
      ret.buttonEvents = create_button_events(self.CS.cruise_buttons[-1], self.CS.prev_cruise_buttons, BUTTONS_DICT)

    # On some newer model years, the CANCEL button acts as a pause/resume button based on the PCM state
    # To avoid re-engaging when openpilot cancels, check user engagement intention via buttons
    # Main button also can trigger an engagement on these cars
    allow_enable = any(btn in ENABLE_BUTTONS for btn in self.CS.cruise_buttons) or any(self.CS.main_buttons) \
                   or self.CP.carFingerprint in CANFD_CAR

    events = self.create_common_events(ret, pcm_enable=self.CS.CP.pcmCruise, allow_enable=allow_enable)

    # low speed steer alert hysteresis logic (only for cars with steer cut off above 10 m/s)
    if ret.vEgo < (self.CP.minSteerSpeed + 2.) and self.CP.minSteerSpeed > 10.:
      self.low_speed_alert = True
    if ret.vEgo > (self.CP.minSteerSpeed + 4.):
      self.low_speed_alert = False
    if self.low_speed_alert:
      events.add(car.CarEvent.EventName.belowSteerSpeed)

    ret.events = events.to_msg()

    return ret

  def apply(self, c, now_nanos):
    return self.CC.update(c, self.CS, now_nanos)

  @staticmethod
  def get_params_adjust_set_speed():
    return [8, 10], [12, 14, 16, 18]

  def create_buttons(self, button):

    if self.CP.carFingerprint in CANFD_CAR:
      if self.CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS:
        return self.create_buttons_can_fd_alt(button)
      return self.create_buttons_can_fd(button)
    else:
      return self.create_buttons_can(button)

  def get_buttons_dict(self):
    return BUTTONS_DICT

  def create_buttons_can(self, button):
    values = self.CS.clu11
    values["CF_Clu_CruiseSwState"] = button
    values["CF_Clu_AliveCnt1"] = (values["CF_Clu_AliveCnt1"] + 1) % 0x10
    return self.CC.packer.make_can_msg("CLU11", self.CP.sccBus, values)

  def create_buttons_can_fd(self, button):
    values = {
      "COUNTER": self.CS.buttons_counter+1,
      "SET_ME_1": 1,
      "CRUISE_BUTTONS": button,
    }
    return self.CC.packer.make_can_msg("CRUISE_BUTTONS", 5, values)

  def create_buttons_can_fd_alt(self, button):
    return None

