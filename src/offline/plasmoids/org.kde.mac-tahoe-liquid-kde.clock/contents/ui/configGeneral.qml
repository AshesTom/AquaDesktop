import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_showDate: showDate.checked
    property alias cfg_showSeconds: showSeconds.checked

    Kirigami.FormLayout {
        QQC2.CheckBox {
            id: showDate
            Kirigami.FormData.label: i18n("Menu bar:")
            text: i18n("Show date")
        }
        QQC2.CheckBox {
            id: showSeconds
            text: i18n("Show seconds")
        }
    }
}
