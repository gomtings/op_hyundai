#include "ntunewidget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFile>
#include <QSettings>
#include <cmath>
#include <QDebug>

#define QSETTING_ORGINIZATION "ntune"

nTuneWidget::nTuneWidget(const TuneItemInfo &itemInfo, QWidget *parent) :
    QWidget(parent), itemInfo(itemInfo)  {
    setupUi();
    connectSignals();
}

void nTuneWidget::setupUi() {

    setMaximumWidth(1200);

    auto mainLayout = new QVBoxLayout(this);
    // Step Scale Layout
    auto stepScaleLayout = new QHBoxLayout();
    labelStepScale = new QLabel("Step Scale:");
    spinnerStepScale = new QComboBox();
    spinnerStepScale->addItems({"x0.01", "x0.1", "x0.5", "x1", "x5", "x10"});
    stepScaleLayout->addWidget(labelStepScale);
    stepScaleLayout->addWidget(spinnerStepScale);
    //mainLayout->addLayout(stepScaleLayout);

    labelStepScale->setText(QString("Step: %1").arg(getStep(), 0, 'f', 2));
    spinnerStepScale->setCurrentIndex(QSettings(QSETTING_ORGINIZATION).value(getSaveKey(), 3).toInt());

    // Reset Button
    btnReset = new QPushButton("Reset");
    mainLayout->addWidget(btnReset, 0, Qt::AlignRight);

    btnReset->setStyleSheet(R"(
        QPushButton {
            padding: 20px;
            font-size: 55px;
            font-weight: bold;
            background-color: gray;
            color: white;
            border-style: solid;
            border-width: 0px;
            border-radius: 10px;
            border-color: black;
        }
    )");

    // Key, Description, Min~Max, Value Layout
    QVBoxLayout *valueLayout = new QVBoxLayout();
    valueLayout->setSizeConstraint(QLayout::SetMinimumSize);
    valueLayout->setContentsMargins(0, 20, 0, 20);

    QLabel *textKey = new QLabel("Key");
    textKey->setAlignment(Qt::AlignCenter);
    textKey->setStyleSheet("QLabel { font-weight: bold; font-size: 70px; margin: 0px; padding: 5px;}");
    QLabel *textDesc = new QLabel("Description");
    textDesc->setAlignment(Qt::AlignCenter);
    textDesc->setStyleSheet("QLabel { font-size: 50px; margin: 0px; padding: 5px; }");
    textDesc->setWordWrap(true);
    textDesc->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
    QLabel *textMinMax = new QLabel("MinMax");
    textMinMax->setAlignment(Qt::AlignCenter);
    textMinMax->setStyleSheet("QLabel { font-size: 55px; margin: 0px; padding: 5px;}");

    valueLayout->addItem(new QSpacerItem(0, 0, QSizePolicy::Expanding, QSizePolicy::MinimumExpanding));
    valueLayout->addWidget(textKey);
    if(!itemInfo.desc.isEmpty())
        valueLayout->addWidget(textDesc);
    valueLayout->addWidget(textMinMax);

    // Value Display
    textValue = new QLabel("--");
    textValue->setAlignment(Qt::AlignCenter);
    textValue->setStyleSheet("QLabel { font-weight: bold; font-size: 75px; color: #50B050; margin: 0px; padding: 5px; }");
    valueLayout->addWidget(textValue);

    valueLayout->addItem(new QSpacerItem(0, 0, QSizePolicy::Expanding, QSizePolicy::MinimumExpanding));

    // Increase & Decrease Buttons
    QHBoxLayout *controlLayout = new QHBoxLayout();
    btnDecrease = new QPushButton(tr("Decrease(-)"));
    btnIncrease = new QPushButton(tr("Increase(+)"));

    auto btnStyle = R"(
        QPushButton {
            padding: 30px;
            font-size: 55px;
            font-weight: bold;
            background-color: gray;
            color: white;
            border-style: solid;
            border-width: 0px;
            border-radius: 10px;
            border-color: black;
        }
    )";


    btnDecrease->setStyleSheet(btnStyle);
    btnIncrease->setStyleSheet(btnStyle);


    controlLayout->addWidget(btnDecrease);
    controlLayout->addWidget(btnIncrease);

    mainLayout->addLayout(valueLayout);
    mainLayout->addLayout(controlLayout);

    //
    textKey->setText(itemInfo.key);
    textDesc->setText(itemInfo.desc);
    textMinMax->setText(itemInfo.getMinMaxText());

    reload();
}

void nTuneWidget::connectSignals() {
    connect(btnIncrease, &QPushButton::clicked, this, &nTuneWidget::onIncreaseClicked);
    connect(btnDecrease, &QPushButton::clicked, this, &nTuneWidget::onDecreaseClicked);
    connect(btnReset, &QPushButton::clicked, this, &nTuneWidget::onResetClicked);
    connect(spinnerStepScale, static_cast<void (QComboBox::*)(int)>(&QComboBox::currentIndexChanged), this, &nTuneWidget::onStepIndexChanged);

}

QString nTuneWidget::getSaveKey() {
    return QString("item_step_scale_%1").arg(itemInfo.key);
}

float nTuneWidget::getStep() {
    try {
        auto index = QSettings(QSETTING_ORGINIZATION).value(getSaveKey(), 3).toInt();
        float v[] = {0.01f, 0.1f, 0.5f, 1.0f, 5.0f, 10.0f};
        return itemInfo.step * v[index];
    } catch(...){}
    return itemInfo.step;
}

void nTuneWidget::onIncreaseClicked() {
    increase(getStep());
}

void nTuneWidget::onDecreaseClicked() {
    increase(-getStep());
}

void nTuneWidget::onResetClicked() {
    reset();
}

void nTuneWidget::onStepIndexChanged(int index) {
    QSettings(QSETTING_ORGINIZATION).setValue(getSaveKey(), index);
    labelStepScale->setText(QString("Step: %1").arg(getStep(), 0, 'f', 2));
}

QJsonObject nTuneWidget::load() {
    QFile file(itemInfo.fullPath());
    if (!file.open(QIODevice::ReadOnly)) {
        qDebug() << "Failed to open" << itemInfo.fullPath();
        return QJsonObject();
    }

    QByteArray fileContent = file.readAll();
    file.close();

    QJsonDocument jsonDoc = QJsonDocument::fromJson(fileContent);
    if (jsonDoc.isNull()) {
        qDebug() << "Failed to create JSON doc.";
        return QJsonObject();
    }
    if (!jsonDoc.isObject()) {
        qDebug() << "JSON is not an object.";
        return QJsonObject();
    }

    return jsonDoc.object();
}

void nTuneWidget::increase(float step) {

    auto json = load();
    if (!json.contains(itemInfo.key)) {
        json[itemInfo.key] = itemInfo.defValue;
    }

    float value = json.value(itemInfo.key).toDouble(itemInfo.defValue);

    value += step;
    value = std::round(value * std::pow(10, itemInfo.precision)) / std::pow(10, itemInfo.precision);

    if (value < itemInfo.min) value = itemInfo.min;
    if (value > itemInfo.max) value = itemInfo.max;

    update(json, value);
}

void nTuneWidget::reset() {

    auto json = load();
    if (json.contains(itemInfo.key)) {
        json.remove(itemInfo.key);
        save(json);
    }

    float value = json.value(itemInfo.key).toDouble(itemInfo.defValue);
    textValue->setText(itemInfo.toString(value));
}

void nTuneWidget::update(QJsonObject json, float value) {
    json[itemInfo.key] = value;
    textValue->setText(itemInfo.toString(value));
    save(json);
}

void nTuneWidget::reload() {
    auto json = load();
    float value = json.value(itemInfo.key).toDouble(itemInfo.defValue);
    textValue->setText(itemInfo.toString(value));
}

void nTuneWidget::save(QJsonObject json) {
    QFile file(itemInfo.fullPath());
    if (!file.open(QIODevice::WriteOnly)) {
        qWarning() << "Could not open file for writing:" << itemInfo.fullPath();
        return;
    }

    QJsonDocument doc(json);
    file.write(doc.toJson());
    file.close();
}
