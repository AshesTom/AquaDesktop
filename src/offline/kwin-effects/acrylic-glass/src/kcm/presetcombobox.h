// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <QComboBox>

class PresetComboBox : public QComboBox
{
    Q_OBJECT
    Q_PROPERTY(int presetValue READ presetValue WRITE setPresetValue NOTIFY presetValueChanged USER true)

public:
    explicit PresetComboBox(QWidget *parent = nullptr)
        : QComboBox(parent)
    {
        connect(this, &QComboBox::currentIndexChanged, this, [this] {
            Q_EMIT presetValueChanged(presetValue());
        });
    }

    int presetValue() const { return currentData().toInt(); }
    void setPresetValue(int value)
    {
        const int index = findData(value);
        // Retired or unknown selections fall back to Tahoe without resetting optics.
        setCurrentIndex(index < 0 ? 0 : index);
    }

Q_SIGNALS:
    void presetValueChanged(int value);
};
