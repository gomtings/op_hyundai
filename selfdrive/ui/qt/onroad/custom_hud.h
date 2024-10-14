#pragma once

#include <QPainter>
#include "selfdrive/ui/ui.h"

class CustomHudRenderer : public QObject {
  Q_OBJECT

public:
  CustomHudRenderer();
  void updateState(const UIState &s);
  void draw(QPainter &p, const QRect &surface_rect);

private:
  void drawText(QPainter &p, int x, int y, const QString &text, int alpha = 255);
  void drawText2(QPainter &p, int x, int y, int flags, const QString &text, const QColor& color);
  void drawTextWithColor(QPainter &p, int x, int y, const QString &text, QColor& color);
  void drawRoundedText(QPainter &p, int x, int y, const QString &text, QColor& color, QColor& bgColor, int cornerRadius);

  const int radius = 192;
  const int img_size = (radius / 2) * 1.5;

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

  void drawMaxSpeed(QPainter &p, const QRect &rect);
  void drawSpeed(QPainter &p, const QRect &rect);
  void drawBottomIcons(QPainter &p, const QRect &rect);
  void drawSteer(QPainter &p, const QRect &rect);
  void drawDeviceState(QPainter &p, const QRect &rect);
  void drawTurnSignals(QPainter &p, const QRect &rect);
  void drawGpsStatus(QPainter &p, const QRect &rect);
  void drawDebugText(QPainter &p, const QRect &rect);
  void drawMisc(QPainter &p, const QRect &rect);
  bool drawTrafficSignal(QPainter &p, const QRect &rect);
  void drawHud(QPainter &p, const QRect &rect);
};
