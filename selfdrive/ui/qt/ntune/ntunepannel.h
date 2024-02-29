#pragma once

#include <QWidget>
#include <QTabBar>
#include <QStackedWidget>
#include <QVBoxLayout>
#include <QMouseEvent>
#include <QGesture>
#include <QListView>
#include <QStyledItemDelegate>
#include "ntunewidget.h"

class BoldItemDelegate : public QStyledItemDelegate {
public:
    using QStyledItemDelegate::QStyledItemDelegate;

    void paint(QPainter *painter, const QStyleOptionViewItem &option, const QModelIndex &index) const override {
        QStyleOptionViewItem optionV4 = option;
        initStyleOption(&optionV4, index);
        QFont font = optionV4.font;
        font.setBold(true);
        optionV4.font = font;
        QStyledItemDelegate::paint(painter, optionV4, index);
    }
};

class nTuneMainWidget : public QWidget {
    Q_OBJECT
public:
    explicit nTuneMainWidget(QWidget *parent = nullptr);

private:
    QListView* listView;
    QStackedWidget *stackedWidget;
};

class nTunePannel : public QWidget
{
    Q_OBJECT
public:
    explicit nTunePannel(QList<TuneItemInfo>& items, QWidget *parent = nullptr);

private:
    QTabBar *tabBar;
    QStackedWidget *stackedWidget;
    QPoint startPos;

protected:
    void mousePressEvent(QMouseEvent *event) override {
        startPos = event->pos();
    }

    void mouseReleaseEvent(QMouseEvent *event) override {
        const int SWIPE_THRESHOLD = 50;
        int distance = event->pos().x() - startPos.x();

        if (abs(distance) > SWIPE_THRESHOLD) {
            if (distance > 0) {
                int prevIndex = tabBar->currentIndex() - 1;
                if (prevIndex >= 0) {
                    tabBar->setCurrentIndex(prevIndex);
                }
            } else {
                int nextIndex = tabBar->currentIndex() + 1;
                if (nextIndex < tabBar->count()) {
                    tabBar->setCurrentIndex(nextIndex);
                }
            }
        }
    }
signals:
};

