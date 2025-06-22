from opendbc_repo.opendbc.car.hyundai.values import CAMERA_SCC_CAR
from opendbc.car import Bus, get_safety_config, structs
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import HyundaiFlags, CAR, DBC, \
  CANFD_UNSUPPORTED_LONGITUDINAL_CAR, \
  UNSUPPORTED_LONGITUDINAL_CAR, HyundaiSafetyFlags, Buttons, CANFD_RADAR_SCC_CAR
from opendbc.car.hyundai.radar_interface import RADAR_START_ADDR
from opendbc.car.interfaces import CarInterfaceBase, ACCEL_MIN, ACCEL_MAX
from opendbc.car.disable_ecu import disable_ecu
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.radar_interface import RadarInterface

from openpilot.common.conversions import Conversions as CV
from openpilot.selfdrive.controls.neokii.cruise_state_manager import is_radar_disabler
from openpilot.common.params import Params
from opendbc.car.hyundai.values import HyundaiExFlags
from common.numpy_fast import interp
import copy

ButtonType = structs.CarState.ButtonEvent.Type
Ecu = structs.CarParams.Ecu

# Cancel button can sometimes be ACC pause/resume button, main button can also enable on some cars
ENABLE_BUTTONS = (ButtonType.accelCruise, ButtonType.decelCruise, ButtonType.cancel, ButtonType.mainCruise)

BUTTONS_DICT = {Buttons.RES_ACCEL: ButtonType.accelCruise, Buttons.SET_DECEL: ButtonType.decelCruise,
                Buttons.GAP_DIST: ButtonType.gapAdjustCruise, Buttons.CANCEL: ButtonType.cancel}


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController
  RadarInterface = RadarInterface

  @staticmethod
  def get_pid_accel_limits(CP, current_speed, cruise_speed):
    v_current_kph = current_speed * CV.MS_TO_KPH
    gas_max_bp = [0., 10., 30., 70., 130., 150.]
    gas_max_v = [ACCEL_MAX, 1.5, 1.0, 0.5, 0.15, 0.1]
    return ACCEL_MIN, interp(v_current_kph, gas_max_bp, gas_max_v)

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate, fingerprint, car_fw, alpha_long, is_release, docs) -> structs.CarParams:
    ret.brand = "hyundai"

    # "LKA steering" if LKAS or LKAS_ALT messages are seen coming from the camera.
    # Generally means our LKAS message is forwarded to another ECU (commonly ADAS ECU)
    # that finally retransmits our steering command in LFA or LFA_ALT to the MDPS.
    # "LFA steering" if camera directly sends LFA to the MDPS
    cam_can = CanBus(None, fingerprint).CAM
    lka_steering = 0x50 in fingerprint[cam_can] or 0x110 in fingerprint[cam_can] or Params().get_bool('CanFdHda2')
    CAN = CanBus(None, fingerprint, lka_steering)

    if ret.flags & HyundaiFlags.CANFD:
      # Shared configuration for CAN-FD cars
      ret.alphaLongitudinalAvailable = candidate not in CANFD_UNSUPPORTED_LONGITUDINAL_CAR
      if lka_steering and Ecu.adas not in [fw.ecu for fw in car_fw]:
        # this needs to be figured out for cars without an ADAS ECU
        ret.alphaLongitudinalAvailable = False

      ret.enableBsm = 0x1e5 in fingerprint[CAN.ECAN]

      if 0x105 in fingerprint[CAN.ECAN]:
        ret.flags |= HyundaiFlags.HYBRID.value

      if lka_steering:
        # detect LKA steering
        ret.flags |= HyundaiFlags.CANFD_LKA_STEERING.value
        if 0x110 in fingerprint[CAN.CAM]:
          ret.flags |= HyundaiFlags.CANFD_LKA_STEERING_ALT.value
      else:
        # no LKA steering
        if candidate not in CANFD_RADAR_SCC_CAR:
          ret.flags |= HyundaiFlags.CANFD_CAMERA_SCC.value

      if 0x1cf not in fingerprint[CAN.ECAN]:
        ret.flags |= HyundaiFlags.CANFD_ALT_BUTTONS.value

      # Some LKA steering cars have alternative messages for gear checks
      # ICE cars do not have 0x130; GEARS message on 0x40 or 0x70 instead
      if 0x130 not in fingerprint[CAN.ECAN]:
        if 0x40 not in fingerprint[CAN.ECAN]:
          ret.flags |= HyundaiFlags.CANFD_ALT_GEARS_2.value
        else:
          ret.flags |= HyundaiFlags.CANFD_ALT_GEARS.value

    ret.radarUnavailable = RADAR_START_ADDR not in fingerprint[1] or Bus.radar not in DBC[ret.carFingerprint]
    ret.steerActuatorDelay = 0.2  # Default delay
    ret.steerLimitTimer = 0.4
    CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    # *** longitudinal control ***
    if ret.flags & HyundaiFlags.CANFD:
      ret.longitudinalTuning.kpBP = [0.]
      ret.longitudinalTuning.kpV = [0.8]
      ret.longitudinalTuning.kf = 0.5
      ret.alphaLongitudinalAvailable = candidate not in (CANFD_UNSUPPORTED_LONGITUDINAL_CAR | CANFD_RADAR_SCC_CAR)
    else:
      ret.longitudinalTuning.kpBP = [0.]
      ret.longitudinalTuning.kpV = [0.9]
      ret.longitudinalTuning.kf = 0.5
      ret.alphaLongitudinalAvailable = True #candidate not in (LEGACY_SAFETY_MODE_CAR)

    ret.openpilotLongitudinalControl = alpha_long and ret.alphaLongitudinalAvailable
    ret.pcmCruise = not ret.openpilotLongitudinalControl

    ret.startingState = True
    ret.stoppingDecelRate = 0.3
    ret.steerActuatorDelay = 0.2
    ret.steerLimitTimer = 2.0

    ret.vEgoStarting = 0.1
    ret.vEgoStopping = 0.1
    ret.startAccel = 1.0
    ret.longitudinalActuatorDelay = 0.5

    # *** feature detection ***
    if ret.flags & HyundaiFlags.CANFD:
      ret.enableBsm = 0x1e5 in fingerprint[CAN.ECAN]
    else:
      ret.enableBsm = 0x58b in fingerprint[0]

    ret.sccBus = 2 if (candidate in CAMERA_SCC_CAR or Params().get_bool('SccOnBus2')) else 0

    # *** panda safety config ***
    if ret.flags & HyundaiFlags.CANFD:
      cfgs = [get_safety_config(structs.CarParams.SafetyModel.hyundaiCanfd), ]
      if CAN.ECAN >= 4:
        cfgs.insert(0, get_safety_config(structs.CarParams.SafetyModel.noOutput))
      ret.safetyConfigs = cfgs

      if ret.flags & HyundaiFlags.CANFD_LKA_STEERING:
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CANFD_LKA_STEERING.value
        if ret.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT:
          ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CANFD_LKA_STEERING_ALT.value
      if ret.flags & HyundaiFlags.CANFD_ALT_BUTTONS:
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CANFD_ALT_BUTTONS.value
      if ret.flags & HyundaiFlags.CANFD_CAMERA_SCC:
        ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.CAMERA_SCC.value

      if ret.sccBus == 2:
        ret.openpilotLongitudinalControl = True
        ret.radarUnavailable = False

      if 0x60 in fingerprint[CAN.ECAN]:
        ret.exFlags |= HyundaiExFlags.AUTOHOLD.value
      if 0x3a0 in fingerprint[CAN.ECAN]:
        ret.exFlags |= HyundaiExFlags.TPMS.value

    else:
      # Shared configuration for non CAN-FD cars
      ret.alphaLongitudinalAvailable = candidate not in UNSUPPORTED_LONGITUDINAL_CAR
      ret.enableBsm = 0x58b in fingerprint[0]

      # Send LFA message on cars with HDA
      if 0x485 in fingerprint[2]:
        ret.flags |= HyundaiFlags.SEND_LFA.value

      # These cars use the FCA11 message for the AEB and FCW signals, all others use SCC12
      if 0x38d in fingerprint[0] or 0x38d in fingerprint[2]:
        ret.flags |= HyundaiFlags.USE_FCA.value

      if ret.flags & HyundaiFlags.LEGACY:
        # these cars require a special panda safety mode due to missing counters and checksums in the messages
        ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.hyundaiLegacy)]
      else:
        ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.hyundai, 0)]

      if ret.flags & HyundaiFlags.CAMERA_SCC:
        ret.safetyConfigs[0].safetyParam |= HyundaiSafetyFlags.CAMERA_SCC.value

      # These cars have the LFA button on the steering wheel
      if 0x391 in fingerprint[0]:
        ret.flags |= HyundaiFlags.HAS_LDA_BUTTON.value

      if 1151 in fingerprint[0]:
        ret.exFlags |= HyundaiExFlags.AUTOHOLD.value
      if 1427 in fingerprint[0]:
        ret.exFlags |= HyundaiExFlags.TPMS.value
      if 1348 in fingerprint[0]:
        ret.exFlags |= HyundaiExFlags.NAVI.value

      if not ret.openpilotLongitudinalControl:
        ret.radarUnavailable = ret.sccBus == -1

      if ret.sccBus == 2:
        if 1290 in fingerprint[0] or 1290 in fingerprint[2]:
          ret.exFlags |= HyundaiExFlags.SCC13.value
        if 905 in fingerprint[0] or 905 in fingerprint[2]:
          ret.exFlags |= HyundaiExFlags.SCC14.value
        ret.openpilotLongitudinalControl = True
        ret.radarUnavailable = False
        ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.hyundaiLegacy)]


    if ret.flags & HyundaiFlags.ALT_LIMITS:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.ALT_LIMITS.value

    if ret.flags & HyundaiFlags.ALT_LIMITS_2:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.ALT_LIMITS_2.value


    if ret.openpilotLongitudinalControl and ret.sccBus == 0 and not Params().get_bool('CruiseStateControl'):
      ret.pcmCruise = False
    else:
      ret.pcmCruise = True # managed by cruise state manager

    if ret.openpilotLongitudinalControl:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.LONG.value
    if ret.flags & HyundaiFlags.HYBRID:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.HYBRID_GAS.value
    elif ret.flags & HyundaiFlags.EV:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.EV_GAS.value
    elif ret.flags & HyundaiFlags.FCEV:
      ret.safetyConfigs[-1].safetyParam |= HyundaiSafetyFlags.FCEV_GAS.value

    if ret.centerToFront == 0:
      ret.centerToFront = ret.wheelbase * 0.4

    return ret

  @staticmethod
  def init(CP, can_recv, can_send):
    if is_radar_disabler(CP) and not (CP.flags & (HyundaiFlags.CANFD_CAMERA_SCC | HyundaiFlags.CAMERA_SCC)):
      addr, bus = 0x7d0, CanBus(CP).ECAN if CP.flags & HyundaiFlags.CANFD else 0
      if CP.flags & HyundaiFlags.CANFD_LKA_STEERING.value:
        addr, bus = 0x730, CanBus(CP).ECAN
      disable_ecu(can_recv, can_send, bus=bus, addr=addr, com_cont_req=b'\x28\x83\x01')

    # for blinkers
    if CP.flags & HyundaiFlags.ENABLE_BLINKERS:
      disable_ecu(can_recv, can_send, bus=CanBus(CP).ECAN, addr=0x7B1, com_cont_req=b'\x28\x83\x01')


  @staticmethod
  def get_params_adjust_set_speed(CP):
    if CP.flags & HyundaiFlags.CANFD:
      return [16], [20]
    return [16, 20], [12, 14, 16, 18]

  def create_buttons(self, button):
    if self.CP.flags & HyundaiFlags.CANFD:
      if self.CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS:
        return self.create_buttons_can_fd_alt(button)
      return self.create_buttons_can_fd(button)
    else:
      return self.create_buttons_can(button)

  def get_buttons_dict(self):
    return BUTTONS_DICT

  def create_buttons_can(self, button):
    values = copy.copy(self.CS.clu11)
    values["CF_Clu_CruiseSwState"] = button
    values["CF_Clu_AliveCnt1"] = (values["CF_Clu_AliveCnt1"] + 1) % 0x10
    return self.CC.packer.make_can_msg("CLU11", self.CP.sccBus, values)

  def create_buttons_can_fd(self, button):
    values = {
      "COUNTER": self.CS.buttons_counter + 1,
      "SET_ME_1": 1,
      "CRUISE_BUTTONS": button,
    }
    bus = self.CC.CAN.ECAN if self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING else self.CC.CAN.CAM
    return self.CC.packer.make_can_msg("CRUISE_BUTTONS", bus, values)

  def create_buttons_can_fd_alt(self, button):
    values = copy.copy(self.CS.canfd_buttons)
    values["CRUISE_BUTTONS"] = button
    values["COUNTER"] = (values["COUNTER"] + 1) % 256
    bus = self.CC.CAN.ECAN if self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING else self.CC.CAN.CAM
    return self.CC.packer.make_can_msg("CRUISE_BUTTONS_ALT", bus, values)

