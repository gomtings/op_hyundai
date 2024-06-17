from cereal import car
from openpilot.common.numpy_fast import clip, interp
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N
from openpilot.selfdrive.controls.lib.pid import PIDController
from openpilot.selfdrive.modeld.constants import ModelConstants

CONTROL_N_T_IDX = ModelConstants.T_IDXS[:CONTROL_N]

LongCtrlState = car.CarControl.Actuators.LongControlState


def long_control_state_trans(CP, active, long_control_state, v_ego,
                             should_stop, brake_pressed, cruise_standstill, lead):
  stopping_condition = should_stop
  starting_condition = (not should_stop and
                        not cruise_standstill and
                        not brake_pressed) and (lead.vLeadK > 0.3 and lead.dRel > 4.)
  started_condition = v_ego > CP.vEgoStarting

  if not active:
    long_control_state = LongCtrlState.off

  else:
    if long_control_state in (LongCtrlState.off, LongCtrlState.pid):
      long_control_state = LongCtrlState.pid
      if stopping_condition:
        long_control_state = LongCtrlState.stopping
    elif long_control_state == LongCtrlState.stopping:
      if starting_condition and CP.startingState and v_ego < 0.01:
        long_control_state = LongCtrlState.starting
      elif starting_condition:
        long_control_state = LongCtrlState.pid

    elif long_control_state == LongCtrlState.starting:
      if stopping_condition:
        long_control_state = LongCtrlState.stopping
      elif started_condition:
        long_control_state = LongCtrlState.pid

  return long_control_state

class LongControl:
  def __init__(self, CP):
    self.CP = CP
    self.long_control_state = LongCtrlState.off
    self.pid = PIDController((CP.longitudinalTuning.kpBP, CP.longitudinalTuning.kpV),
                             (CP.longitudinalTuning.kiBP, CP.longitudinalTuning.kiV),
                             k_f=CP.longitudinalTuning.kf, rate=1 / DT_CTRL)
    self.last_output_accel = 0.0
    self.stopping_accel_weight = 0.0
    self.prev_long_control_state = self.long_control_state

  def reset(self):
    self.pid.reset()

  def update(self, active, CS, a_target, should_stop, accel_limits, sm):
    """Update longitudinal control. This updates the state machine and runs a PID loop"""
    self.pid.neg_limit = accel_limits[0]
    self.pid.pos_limit = accel_limits[1]

    self.prev_long_control_state = self.long_control_state
    self.long_control_state = long_control_state_trans(self.CP, active, self.long_control_state, CS.vEgo,
                                                       should_stop, CS.brakePressed,
                                                       CS.cruiseState.standstill, sm['radarState'].leadOne)
    if self.long_control_state == LongCtrlState.off:
      self.reset()
      output_accel = 0.
      self.stopping_accel_weight = 0.0

    elif self.long_control_state == LongCtrlState.stopping:
      output_accel = self.last_output_accel
      if output_accel > self.CP.stopAccel:
        output_accel = min(output_accel, 0.0)
        self.stopping_accel_weight = 1.0
        if self.prev_long_control_state == LongCtrlState.starting:
          output_accel -= self.CP.stoppingDecelRate * 1.5 * DT_CTRL
        else:
          m_accel = -0.7
          d_accel = interp(output_accel,
                           [m_accel - 0.5, m_accel, m_accel + 0.5],
                           [self.CP.stoppingDecelRate, 0.05, self.CP.stoppingDecelRate])

          output_accel -= d_accel * DT_CTRL
      else:
        self.stopping_accel_weight = 0.0

      self.reset()

    elif self.long_control_state == LongCtrlState.starting:
      output_accel = self.CP.startAccel
      self.reset()
      self.stopping_accel_weight = 0.0

    else:  # LongCtrlState.pid
      error = a_target - CS.aEgo
      output_accel = self.pid.update(error, speed=CS.vEgo,
                                     feedforward=a_target)

      self.stopping_accel_weight = max(self.stopping_accel_weight - 2. * DT_CTRL, 0.)
      output_accel = self.last_output_accel * self.stopping_accel_weight + output_accel * (1. - self.stopping_accel_weight)

    self.last_output_accel = clip(output_accel, accel_limits[0], accel_limits[1])
    return self.last_output_accel
