#pragma once

#include <QVBoxLayout>
#include <memory>

#include "selfdrive/ui/qt/onroad/buttons.h"
#include "selfdrive/ui/qt/onroad/driver_monitoring.h"
#include "selfdrive/ui/qt/widgets/cameraview.h"
#include "selfdrive/ui/qt/screenrecorder/screenrecorder.h"

class AnnotatedCameraWidget : public CameraWidget {
  Q_OBJECT

public:
  explicit AnnotatedCameraWidget(VisionStreamType type, QWidget* parent = 0);
  void updateState(const UIState &s);

protected:
  void paintGL() override;
  void initializeGL() override;
  void showEvent(QShowEvent *event) override;
  mat4 calcFrameMatrix() override;
  void drawLaneLines(QPainter &painter, const UIState *s);
  void drawLead(QPainter &painter, const cereal::RadarState::LeadData::Reader &lead_data, const QPointF &vd, bool is_radar);
  inline QColor redColor(int alpha = 255) { return QColor(201, 34, 49, alpha); }
  inline QColor whiteColor(int alpha = 255) { return QColor(255, 255, 255, alpha); }
  inline QColor blackColor(int alpha = 255) { return QColor(0, 0, 0, alpha); }

  QVBoxLayout *main_layout;
  ExperimentalButton *experimental_btn;
  DriverMonitorRenderer dmon;
  bool dmActive = false;
  bool hideBottomIcons = false;
  bool rightHandDM = false;
  QPixmap dm_img;
  float dm_fade_state = 1.0;

  double prev_draw_t = 0;
  FirstOrderFilter fps_filter;
  std::unique_ptr<PubMaster> pm;

  bool wide_cam_requested = false;

  // neokii
  //void drawIcon(QPainter &p, int x, int y, QPixmap &img, QBrush bg, float opacity);
  void drawText(QPainter &p, int x, int y, const QString &text, int alpha = 255);
  void drawText2(QPainter &p, int x, int y, int flags, const QString &text, const QColor& color);
  void drawTextWithColor(QPainter &p, int x, int y, const QString &text, QColor& color);
  void drawRoundedText(QPainter &p, int x, int y, const QString &text, QColor& color, QColor& bgColor, int cornerRadius);
  void paintEvent(QPaintEvent *event) override;

  const int radius = 192;
  const int img_size = (radius / 2) * 1.5;

  uint64_t last_update_params;

  // neokii
  QPixmap ic_brake;
  QPixmap ic_autohold_warning;
  QPixmap ic_autohold_active;
  QPixmap ic_nda;
  QPixmap ic_hda;
  QPixmap ic_nda2;
  QPixmap ic_hda2;
  QPixmap ic_tire_pressure;
  QPixmap ic_turn_signal_l;
  QPixmap ic_turn_signal_r;
  QPixmap ic_satellite;
  QPixmap ic_safety_speed_bump;
  QPixmap ic_ts_green[2];
  QPixmap ic_ts_left[2];
  QPixmap ic_ts_red[2];

  QMap<QString, QPixmap> ic_oil_com;

  void drawMaxSpeed(QPainter &p);
  void drawSpeed(QPainter &p);
  void drawBottomIcons(QPainter &p);
  void drawSteer(QPainter &p);
  void drawDeviceState(QPainter &p);
  void drawTurnSignals(QPainter &p);
  void drawGpsStatus(QPainter &p);
  void drawDebugText(QPainter &p);
  void drawMisc(QPainter &p);
  bool drawTrafficSignal(QPainter &p);
  void drawHud(QPainter &p, const cereal::ModelDataV2::Reader &model);

  // neokii
private:
  ScreenRecoder* recorder;
  std::shared_ptr<QTimer> record_timer;
  QPoint startPos;
};
