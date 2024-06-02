#pragma once

#include <QWidget>
#include <QLabel>
#include <QPushButton>
#include <QComboBox>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QDataStream>
#include <QJsonObject>
#include <QJsonDocument>

#define CONF_PATH "/data/ntune"

class TuneItemInfo {
private:
    QString confPath;
public:
    QString key;
    QString desc;
    float defValue;
    float min;
    float max;
    float step;
    int precision;
    QString unit;

    TuneItemInfo() : confPath(""), key(""), desc(""), unit(""), defValue(0), min(0), max(0), step(0), precision(0) {}
    TuneItemInfo(QString confPath, QString key, QString desc, float defValue, float min, float max, float step, int precision)
        : confPath(confPath), key(key), desc(desc), defValue(defValue), min(min), max(max), step(step), precision(precision), unit("") {}
    TuneItemInfo(QString confPath, QString key, QString desc, float defValue, float min, float max, float step, int precision, QString unit)
        : confPath(confPath), key(key), desc(desc), defValue(defValue), min(min), max(max), step(step), precision(precision), unit(unit) {}

    QString toString(float value) const {
        return QString("%1%2").arg(value, 0, 'f', precision).arg(unit);
    }

    QString getMinMaxText() const {
        return QString("%1 ~ %2").arg(toString(min), toString(max));
    }

    QString fullPath() const {
        return QString("%1/%2").arg(CONF_PATH, confPath);
    }
};


class nTuneWidget : public QWidget {
    Q_OBJECT

public:
    explicit nTuneWidget(const TuneItemInfo &itemInfo, QWidget *parent = nullptr);

private:
    QPushButton *btnIncrease;
    QPushButton *btnDecrease;
    QPushButton *btnReset;
    QLabel *labelStepScale;
    QComboBox *spinnerStepScale;
    QLabel *textValue;

    TuneItemInfo itemInfo;

    void setupUi();
    void connectSignals();
    void increase(float step);
    void reset();
    void update(QJsonObject json, float value);
    void reload();
    QJsonObject load();
    void save(QJsonObject json);

    QString getSaveKey();
    float getStep();

protected:
    void showEvent(QShowEvent *event) override {
        QWidget::showEvent(event);
        reload();
    }
private slots:
    void onIncreaseClicked();
    void onDecreaseClicked();
    void onResetClicked();
    void onStepIndexChanged(int index);
};

