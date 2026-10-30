import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    Plasmoid.icon: "computer"
    toolTipMainText: "TuskerOS Desktop"
    toolTipSubText: "Desktop shell foundation"

    fullRepresentation: ColumnLayout {
        spacing: 8

        Layout.minimumWidth: 240
        Layout.minimumHeight: 112

        PlasmaComponents.Heading {
            Layout.fillWidth: true
            level: 2
            text: "TuskerOS"
        }

        PlasmaComponents.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Desktop shell foundation"
        }

        PlasmaComponents.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            opacity: 0.8
            text: "Your desktop remains available independently of Tusker AI services."
        }
    }
}
