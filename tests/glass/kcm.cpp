// SPDX-License-Identifier: GPL-3.0-or-later
#include <KCModule>
#include <KConfigGroup>
#include <KPluginFactory>
#include <KSharedConfig>
#include <QApplication>
#include <QCheckBox>
#include <QDoubleSpinBox>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLineEdit>
#include <QPlainTextEdit>
#include <QSlider>
#include <QSpinBox>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <memory>

static void require(bool ok, const QString &message)
{
    if (!ok) {
        fprintf(stderr, "%s\n", qPrintable(message));
        std::exit(1);
    }
}

template <class T> static T *control(KCModule *module, const QString &name)
{
    auto *result = module->widget()->findChild<T *>(name);
    require(result, name + QStringLiteral(" missing"));
    return result;
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    require(argc == 3, QStringLiteral("plugin and preset JSON required"));
    QFile input(QString::fromLocal8Bit(argv[2]));
    require(input.open(QIODevice::ReadOnly), QStringLiteral("presets unreadable"));
    const auto tahoe = QJsonDocument::fromJson(input.readAll()).array().at(0).toObject().value(QStringLiteral("values")).toObject();
    auto config = KSharedConfig::openConfig(QStringLiteral("kwinrc"));
    KConfigGroup group(config, QStringLiteral("Effect-liquidglass"));
    group.writeEntry("TopCornerRadius", 13.5);
    group.writeEntry("WindowClasses", "preserved-app");
    config->sync();
    const KPluginMetaData meta(QString::fromLocal8Bit(argv[1]));
    auto open = [&] {
        auto result = KPluginFactory::instantiatePlugin<KCModule>(meta);
        require(bool(result), result.errorString);
        auto module = std::unique_ptr<KCModule>(result.plugin);
        module->load();
        return module;
    };
    // The schema defaults are the Tahoe material, so a fresh page and
    // Defaults show what installing Tahoe writes.
    const auto verifyTahoe = [&](KCModule *module) {
        for (auto it = tahoe.constBegin(); it != tahoe.constEnd(); ++it) {
            const auto name = QStringLiteral("kcfg_") + it.key();
            auto *widget = control<QWidget>(module, name);
            if (auto *number = qobject_cast<QDoubleSpinBox *>(widget))
                require(std::abs(number->value() - it.value().toDouble()) < 0.00001, name);
            else if (auto *slider = qobject_cast<QSlider *>(widget))
                require(slider->value() == it.value().toInt(), name);
            else if (auto *integer = qobject_cast<QSpinBox *>(widget))
                require(integer->value() == it.value().toInt(), name);
            else if (auto *toggle = qobject_cast<QCheckBox *>(widget))
                require(toggle->isChecked() == it.value().toBool(), name);
            else if (auto *text = qobject_cast<QLineEdit *>(widget))
                require(text->text() == it.value().toString(), name);
            else require(false, name + QStringLiteral(" unknown control type"));
        }
    };
    auto module = open();
    verifyTahoe(module.get());
    require(control<QDoubleSpinBox>(module.get(), QStringLiteral("kcfg_TopCornerRadius"))->value() == 13.5,
            QStringLiteral("loading changed the saved radius"));
    require(control<QPlainTextEdit>(module.get(), QStringLiteral("kcfg_WindowClasses"))->toPlainText() == QStringLiteral("preserved-app"),
            QStringLiteral("loading changed the window rules"));

    control<QSlider>(module.get(), QStringLiteral("kcfg_BlurStrength"))->setValue(9);
    control<QLineEdit>(module.get(), QStringLiteral("kcfg_TintColor"))->setText(QStringLiteral("#26265a81"));
    module->save();
    module.reset();
    module = open();
    require(control<QSlider>(module.get(), QStringLiteral("kcfg_BlurStrength"))->value() == 9, QStringLiteral("reopening resets overrides"));
    require(control<QLineEdit>(module.get(), QStringLiteral("kcfg_TintColor"))->text() == QStringLiteral("#26265a81"), QStringLiteral("custom tint lost"));

    control<QSlider>(module.get(), QStringLiteral("kcfg_BlurStrength"))->setValue(2);
    module->load(); // Cancel discards pending changes.
    require(control<QSlider>(module.get(), QStringLiteral("kcfg_BlurStrength"))->value() == 9, QStringLiteral("cancel failed"));

    module->defaults();
    verifyTahoe(module.get());
    module->save();
    config->reparseConfiguration();
    // KConfig omits values equal to the schema default.
    require(!group.hasKey("BlurStrength") || group.readEntry("BlurStrength", 0) == tahoe["BlurStrength"].toInt(),
            QStringLiteral("restore failed"));
    fprintf(stderr, "Tahoe defaults, save/reopen, cancel and restore verified\n");
}
