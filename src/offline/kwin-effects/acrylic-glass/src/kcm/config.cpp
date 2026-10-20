/*
    SPDX-FileCopyrightText: 2010 Fredrik Höglund <fredrik@kde.org>
    SPDX-License-Identifier: GPL-2.0-or-later
*/
#include "config.h"
#include "glassconfig.h"
#include "presets.h"

#include "kwineffects_interface.h"
#include <KConfigGroup>
#include <KPluginFactory>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

namespace KWin {

K_PLUGIN_CLASS(LiquidGlassEffectConfig)

LiquidGlassEffectConfig::LiquidGlassEffectConfig(QObject* parent, const KPluginMetaData& data)
    : KCModule(parent, data)
{
    ui.setupUi(widget());
    BlurConfig::instance("kwinrc");
    addConfig(BlurConfig::self(), widget());

    // Only a deliberate selection resets the material. Loading a saved preset
    // must retain its individual overrides, including after Cancel or reopening.
    connect(ui.kcfg_MaterialPreset, &QComboBox::activated, this, &LiquidGlassEffectConfig::applyPreset);
    connect(ui.resetPreset, &QPushButton::clicked, this, [this] {
        applyPreset(ui.kcfg_MaterialPreset->currentIndex());
    });
    const auto updateGradient = [this](bool enabled) {
        ui.kcfg_GradientTopColor->setEnabled(enabled);
        ui.kcfg_GradientBottomColor->setEnabled(enabled);
        ui.kcfg_GradientTopOpacity->setEnabled(enabled);
        ui.kcfg_GradientBottomOpacity->setEnabled(enabled);
    };
    connect(ui.kcfg_DarkGradientOverlay, &QCheckBox::toggled, this, updateGradient);
    updateGradient(ui.kcfg_DarkGradientOverlay->isChecked());

    // Keep the filtering mode deterministic even if older configs had both unset.
    if (!ui.kcfg_BlurMatching->isChecked() && !ui.kcfg_BlurNonMatching->isChecked()) {
        ui.kcfg_BlurNonMatching->setChecked(true);
    }
}

LiquidGlassEffectConfig::~LiquidGlassEffectConfig() { }

void LiquidGlassEffectConfig::applyPreset(int index)
{
    const auto presets = QJsonDocument::fromJson(materialPresetsJson).array();
    if (index < 0 || index >= presets.size()) {
        return;
    }
    const auto values = presets.at(index).toObject().value(QStringLiteral("values")).toObject();
    for (auto it = values.constBegin(); it != values.constEnd(); ++it) {
        auto *control = widget()->findChild<QWidget *>(QStringLiteral("kcfg_") + it.key());
        if (auto *number = qobject_cast<QDoubleSpinBox *>(control)) {
            number->setValue(it.value().toDouble());
        } else if (auto *integer = qobject_cast<QSpinBox *>(control)) {
            integer->setValue(it.value().toInt());
        } else if (auto *toggle = qobject_cast<QCheckBox *>(control)) {
            toggle->setChecked(it.value().toBool());
        } else if (auto *color = qobject_cast<KColorButton *>(control)) {
            color->setColor(QColor(it.value().toString()));
        }
    }
}

void LiquidGlassEffectConfig::save()
{
    KCModule::save();

    // KConfigSkeleton removes entries equal to schema defaults. Retain the
    // selection explicitly so a Golden Gate reinstall can distinguish a saved
    // Tahoe material from an installation that has never selected a preset.
    auto group = BlurConfig::self()->config()->group(QStringLiteral("Effect-liquidglass"));
    group.writeEntry("MaterialPreset", ui.kcfg_MaterialPreset->currentIndex());
    group.sync();

    OrgKdeKwinEffectsInterface interface(QStringLiteral("org.kde.KWin"), QStringLiteral("/Effects"), QDBusConnection::sessionBus());

    if (QGuiApplication::platformName() == QStringLiteral("xcb")) {
        interface.reconfigureEffect(QStringLiteral("liquidglass_x11"));
    } else {
        interface.reconfigureEffect(QStringLiteral("liquidglass"));
    }
}

} // namespace KWin

#include "config.moc"
#include "moc_config.cpp"
