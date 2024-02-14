from common.numpy_fast import clip, interp
from cereal import car
from common.realtime import DT_CTRL
from common.conversions import Conversions as CV
from selfdrive.car.hyundai.values import Buttons
from common.params import Params
from selfdrive.controls.lib.lateral_planner import TRAJECTORY_SIZE
#from selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import AUTO_TR_CRUISE_GAP
from selfdrive.car.hyundai.values import CAR
from selfdrive.car.isotp_parallel_query import IsoTpParallelQuery
      
# ajouatom
def enable_radar_tracks(CP, logcan, sendcan):
      # START: Try to enable radar tracks
  print("Try to enable radar tracks")
  if CP.openpilotLongitudinalControl and CP.carFingerprint in [CAR.NEXO]:
    rdr_fw = None
    rdr_fw_address = 0x7d0 #일부차량은 다름..
    if True:
      for i in range(10):
        print("O yes")
      try:
        for i in range(40):
          try:
            query = IsoTpParallelQuery(sendcan, logcan, CP.sccBus, [rdr_fw_address], [b'\x10\x07'], [b'\x50\x07'], debug=True)
            for addr, dat in query.get_data(0.1).items(): # pylint: disable=unused-variable
              print("ecu write data by id ...")
              new_config = b"\x00\x00\x00\x01\x00\x01"
              #new_config = b"\x00\x00\x00\x00\x00\x01"
              dataId = b'\x01\x42'
              WRITE_DAT_REQUEST = b'\x2e'
              WRITE_DAT_RESPONSE = b'\x68'
              query = IsoTpParallelQuery(sendcan, logcan, CP.sccBus, [rdr_fw_address], [WRITE_DAT_REQUEST+dataId+new_config], [WRITE_DAT_RESPONSE], debug=True)
              query.get_data(0)
              print(f"Try {i+1}")
              break
            break
          except Exception as e:
            print(f"Failed {i}: {e}") 
      except Exception as e:
        print("Failed to enable tracks" + str(e))
  print("END Try to enable radar tracks")
  # END try to enable radar tracks
  
"""
def enable_radar_tracks(CP, logcan, sendcan):
      # START: Try to enable radar tracks
  print("Try to enable radar tracks")  
  # if self.CP.openpilotLongitudinalControl and self.CP.carFingerprint in [HYUNDAI_CAR.SANTA_FE_2022]:
  if CP.openpilotLongitudinalControl and CP.carFingerprint in [CAR.SANTA_FE_HEV_2022, CAR.NEXO]:
    rdr_fw = None
    for fw in CP.carFw:
      if fw.ecu == "fwdRadar":
        rdr_fw = fw
        break
    print(f"Found fwdRadar: {rdr_fw.fwVersion}")
    if rdr_fw.fwVersion in [b'\xf1\x8799110S1500\xf1\x00TM__ SCC FHCUP      1.00 1.00 99110-S1500         ',
      b'TM__ SCC FHCUP      1.00 1.00 99110-S1500 \x04!\x15\x07    ',
      b'TMhe SCC FHCUP      1.00 1.00 99110-CL500 \x04$\x164    ', 
      b'\xf1\x00TMhe SCC FHCUP      1.00 1.00 99110-CL500         ', # SANTAFE_HEV
      b'\xf1\x00FE__ SCC FHCUP      1.00 1.03 99110-M5000         ', #NEXO
      b'\xf1\x00FE__ SCC FHCUP      1.00 1.04 99110-M5000         ', #NEXO2
      ]:
      for i in range(10):
        print("O yes")
      try:
        for i in range(40):
          try:
            query = IsoTpParallelQuery(sendcan, logcan, CP.sccBus, [rdr_fw.address], [b'\x10\x07'], [b'\x50\x07'], debug=True)
            for addr, dat in query.get_data(0.1).items(): # pylint: disable=unused-variable
              print("ecu write data by id ...")
              new_config = b"\x00\x00\x00\x01\x00\x01"
              #new_config = b"\x00\x00\x00\x00\x00\x01"
              dataId = b'\x01\x42'
              WRITE_DAT_REQUEST = b'\x2e'
              WRITE_DAT_RESPONSE = b'\x68'
              query = IsoTpParallelQuery(sendcan, logcan, CP.sccBus, [rdr_fw.address], [WRITE_DAT_REQUEST+dataId+new_config], [WRITE_DAT_RESPONSE], debug=True)
              query.get_data(0)
              print(f"Try {i+1}")
              break
            break
          except Exception as e:
            print(f"Failed {i}: {e}") 
      except Exception as e:
        print("Failed to enable tracks" + str(e))
  print("END Try to enable radar tracks")
  # END try to enable radar tracks
"""