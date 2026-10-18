/**
 * Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.
 *
 * This file is part of sunnypilot and is licensed under the MIT License.
 * See the LICENSE.md file in the root directory for more details.
 */

#include "selfdrive/ui/sunnypilot/qt/offroad/settings/lateral_panel.h"

#include "common/util.h"
#include "selfdrive/ui/sunnypilot/qt/widgets/controls.h"

LateralPanel::LateralPanel(SettingsWindowSP *parent) : QFrame(parent) {
  main_layout = new QStackedLayout(this);
  ListWidget *list = new ListWidget(this, false);

  sunnypilotScreen = new QWidget(this);
  QVBoxLayout* vlayout = new QVBoxLayout(sunnypilotScreen);
  vlayout->setContentsMargins(50, 20, 50, 20);

  // MADS
  madsToggle = new ParamControl(
    "Mads",
    tr("Modular Assistive Driving System (MADS)"),
    tr("Enable the beloved MADS feature. Disable toggle to revert back to stock sunnypilot engagement/disengagement."),
    "");
  madsToggle->setConfirmation(true, false);
  list->addItem(madsToggle);

  madsSettingsButton = new PushButtonSP(tr("Customize MADS"));
  madsSettingsButton->setObjectName("mads_btn");
  connect(madsSettingsButton, &QPushButton::clicked, [=]() {
    sunnypilotScroller->setLastScrollPosition();
    main_layout->setCurrentWidget(madsWidget);
  });
  QObject::connect(madsToggle, &ToggleControl::toggleFlipped, madsSettingsButton, &PushButtonSP::setEnabled);

  madsWidget = new MadsSettings(this);
  connect(madsWidget, &MadsSettings::backPress, [=]() {
    sunnypilotScroller->restoreScrollPosition();
    main_layout->setCurrentWidget(sunnypilotScreen);
  });
  list->addItem(madsSettingsButton);

  list->addItem(vertical_space());
  list->addItem(horizontal_line());
  list->addItem(vertical_space());

  // Lane Change Settings
  laneChangeSettingsButton = new PushButtonSP(tr("Customize Lane Change"));
  laneChangeSettingsButton->setObjectName("lane_change_btn");
  connect(laneChangeSettingsButton, &QPushButton::clicked, [=]() {
    sunnypilotScroller->setLastScrollPosition();
    main_layout->setCurrentWidget(laneChangeWidget);
  });

  laneChangeWidget = new LaneChangeSettings(this);
  connect(laneChangeWidget, &LaneChangeSettings::backPress, [=]() {
    sunnypilotScroller->restoreScrollPosition();
    main_layout->setCurrentWidget(sunnypilotScreen);
  });
  list->addItem(laneChangeSettingsButton);

  list->addItem(vertical_space(0));
  list->addItem(horizontal_line());

  // Blinker Pause Lateral Control
  blinkerPauseLateralSettings = new BlinkerPauseLateralSettings(
    "BlinkerPauseLateralControl",
    tr("Pause Lateral Control with Blinker"),
    tr("Pause lateral control with blinker when traveling below the desired speed selected."),
    "",
    this);
  list->addItem(blinkerPauseLateralSettings);

  list->addItem(horizontal_line());

  // Neural Network Lateral Control
  nnlcToggle = new NeuralNetworkLateralControl();
  list->addItem(nnlcToggle);

  QObject::connect(nnlcToggle, &ParamControl::toggleFlipped, [=](bool state) {
    if (state) {
      nnlcToggle->showDescription();
    } else {
      nnlcToggle->hideDescription();
    }

    nnlcToggle->updateToggle();
  });

  list->addItem(horizontal_line());

  // Enforce Torque Lateral Control (torque controller v0/v1)
  torqueToggle = new ParamControl(
    "EnforceTorqueControl",
    tr("Enforce Torque Lateral Control"),
    tr("Enable this to enforce sunnypilot to steer with Torque lateral control. Cannot be used together with NNLC."),
    "");
  torqueToggle->setConfirmation(true, false);
  list->addItem(torqueToggle);

  torqueTuneButtons = new ButtonParamControlSP(
    "TorqueControlTune", tr("Torque Control Tune"),
    tr("v0 is the sunnypilot default. v1 is the newer controller with jerk look-ahead."),
    "",
    {tr("v0 (Default)"), tr("v1")},
    375);
  list->addItem(torqueTuneButtons);

  jerkToggle = new ParamControl(
    "LateralJerkTorqueController",
    tr("Lateral Jerk Torque Controller"),
    tr("Looks ahead at planned steering to reduce sudden corrections, so the wheel moves more smoothly through turns. "
       "Works with Self-Tune and custom tuning. Cannot be used together with NNLC."),
    "");
  list->addItem(jerkToggle);

  selfTuneToggle = new ParamControl(
    "LiveTorqueParamsToggle",
    tr("Self-Tune"),
    tr("Enables self-tune for Torque lateral control for platforms that do not use Torque lateral control by default."),
    "");
  list->addItem(selfTuneToggle);

  relaxedTuneToggle = new ParamControl(
    "LiveTorqueParamsRelaxedToggle",
    tr("Less Restrict Settings for Self-Tune (Beta)"),
    tr("Less strict settings when using Self-Tune. This allows torqued to be more forgiving when learning values."),
    "");
  list->addItem(relaxedTuneToggle);

  customTuneToggle = new ParamControl(
    "CustomTorqueParams",
    tr("Enable Custom Tuning"),
    tr("Enables custom tuning for Torque lateral control. Modifying Lateral Acceleration Factor and Friction below will override "
       "the offline values indicated in the YAML files within opendbc/car/torque_data. "
       "The values will also be used live when the Manual Real-Time Tuning toggle is enabled."),
    "");
  list->addItem(customTuneToggle);

  overrideToggle = new ParamControl(
    "TorqueParamsOverrideEnabled",
    tr("Manual Real-Time Tuning"),
    tr("Enforces the torque lateral controller to use the fixed values instead of the learned values from Self-Tune. "
       "Enabling this toggle overrides Self-Tune values."),
    "");
  list->addItem(overrideToggle);

  // the value controls read their param on construction, so make sure the defaults exist
  if (params.get("TorqueParamsOverrideLatAccelFactor").empty()) params.put("TorqueParamsOverrideLatAccelFactor", std::string("2.5"));
  if (params.get("TorqueParamsOverrideFriction").empty()) params.put("TorqueParamsOverrideFriction", std::string("0.1"));

  latAccelFactorOption = new OptionControlSP(
    "TorqueParamsOverrideLatAccelFactor", tr("Lateral Acceleration Factor"), "", "", {1, 500}, 1, false, nullptr, true);
  frictionOption = new OptionControlSP(
    "TorqueParamsOverrideFriction", tr("Friction"), "", "", {1, 100}, 1, false, nullptr, true);
  list->addItem(latAccelFactorOption);
  list->addItem(frictionOption);

  auto refreshLatAccelLabel = [=]() {
    latAccelFactorOption->setLabel(QString::number(QString::fromStdString(params.get("TorqueParamsOverrideLatAccelFactor")).toFloat(), 'f', 2) + " m/s^2");
  };
  auto refreshFrictionLabel = [=]() {
    frictionOption->setLabel(QString::number(QString::fromStdString(params.get("TorqueParamsOverrideFriction")).toFloat(), 'f', 2));
  };
  QObject::connect(latAccelFactorOption, &OptionControlSP::updateLabels, refreshLatAccelLabel);
  QObject::connect(frictionOption, &OptionControlSP::updateLabels, refreshFrictionLabel);
  refreshLatAccelLabel();
  refreshFrictionLabel();

  QObject::connect(customTuneToggle, &ToggleControl::toggleFlipped, [=](bool state) {
    overrideToggle->setVisible(state);
    latAccelFactorOption->setVisible(state);
    frictionOption->setVisible(state);
  });
  QObject::connect(selfTuneToggle, &ToggleControl::toggleFlipped, [=](bool state) {
    if (!state) {
      params.remove("LiveTorqueParamsRelaxedToggle");
      relaxedTuneToggle->refresh();
    }
    relaxedTuneToggle->setEnabled(state && offroad);
  });

  // Torque control and NNLC replace the same controller, so only one of them can be on
  QObject::connect(torqueToggle, &ToggleControl::toggleFlipped, [=](bool state) {
    torqueTuneButtons->setEnabled(state && offroad);
    if (state && nnlcToggle->isToggled()) {
      params.putBool("NeuralNetworkLateralControl", false);
      nnlcToggle->refresh();
      nnlcToggle->updateToggle();
    }
  });
  QObject::connect(nnlcToggle, &ToggleControl::toggleFlipped, [=](bool state) {
    if (state && torqueToggle->isToggled()) {
      params.putBool("EnforceTorqueControl", false);
      torqueToggle->refresh();
      torqueTuneButtons->setEnabled(false);
    }
    if (state) {
      params.putBool("LateralJerkTorqueController", false);
      jerkToggle->refresh();
    }
    jerkToggle->setEnabled(!state && offroad);
  });

  toggleOffroadOnly = {
    madsToggle, nnlcToggle, torqueToggle, selfTuneToggle, customTuneToggle, overrideToggle,
  };
  QObject::connect(uiState(), &UIState::offroadTransition, this, &LateralPanel::updateToggles);

  sunnypilotScroller = new ScrollViewSP(list, this);
  vlayout->addWidget(sunnypilotScroller);

  main_layout->addWidget(sunnypilotScreen);
  main_layout->addWidget(madsWidget);
  main_layout->addWidget(laneChangeWidget);

  setStyleSheet(R"(
    #back_btn {
      font-size: 50px;
      margin: 0px;
      padding: 15px;
      border-width: 0;
      border-radius: 30px;
      color: #dddddd;
      background-color: #393939;
    }
    #back_btn:pressed {
      background-color:  #4a4a4a;
    }
  )");

  main_layout->setCurrentWidget(sunnypilotScreen);
}

void LateralPanel::showEvent(QShowEvent *event) {
  nnlcToggle->updateToggle();
  updateToggles(offroad);
}

void LateralPanel::hideEvent(QHideEvent *event) {
  main_layout->setCurrentWidget(sunnypilotScreen);
}

void LateralPanel::updateToggles(bool _offroad) {
  for (auto *toggle : toggleOffroadOnly) {
    toggle->setEnabled(_offroad);
  }

  bool angle_steering = false;
  auto cp_bytes = params.get("CarParamsPersistent");
  if (!cp_bytes.empty()) {
    AlignedBuffer aligned_buf;
    capnp::FlatArrayMessageReader cmsg(aligned_buf.align(cp_bytes.data(), cp_bytes.size()));
    cereal::CarParams::Reader CP = cmsg.getRoot<cereal::CarParams>();

    // torque lateral control does not apply to angle steering platforms
    if (CP.getSteerControlType() == cereal::CarParams::SteerControlType::ANGLE) {
      angle_steering = true;
      params.remove("EnforceTorqueControl");
      params.remove("LateralJerkTorqueController");
      torqueToggle->refresh();
      jerkToggle->refresh();
      torqueToggle->setEnabled(false);
    }

    if (isBrandInList(CP.getBrand(), mads_limited_settings_brands)) {
      madsToggle->setDescription(descriptionBuilder(STATUS_MADS_SETTINGS_LIMITED_COMPATIBILITY, MADS_BASE_DESC));
    } else {
      madsToggle->setDescription(descriptionBuilder(STATUS_MADS_SETTINGS_FULL_COMPATIBILITY, MADS_BASE_DESC));
    }
  } else {
    madsToggle->setDescription(descriptionBuilder(STATUS_MADS_CHECK_COMPATIBILITY, MADS_BASE_DESC));
  }

  madsSettingsButton->setEnabled(madsToggle->isToggled());
  torqueTuneButtons->setEnabled(_offroad && torqueToggle->isToggled());

  jerkToggle->setEnabled(_offroad && !nnlcToggle->isToggled() && !angle_steering);
  if (!selfTuneToggle->isToggled()) {
    params.remove("LiveTorqueParamsRelaxedToggle");
    relaxedTuneToggle->refresh();
  }
  relaxedTuneToggle->setEnabled(_offroad && selfTuneToggle->isToggled());

  const bool custom_tuning = customTuneToggle->isToggled();
  overrideToggle->setVisible(custom_tuning);
  latAccelFactorOption->setVisible(custom_tuning);
  frictionOption->setVisible(custom_tuning);
  const bool values_editable = _offroad || overrideToggle->isToggled();
  latAccelFactorOption->setEnabled(values_editable);
  frictionOption->setEnabled(values_editable);

  blinkerPauseLateralSettings->refresh();

  offroad = _offroad;
}
