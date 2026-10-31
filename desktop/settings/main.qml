import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ApplicationWindow {
    id: window
    width: 620; height: 680; minimumWidth: 520; minimumHeight: 560
    visible: true
    title: qsTr("TuskerOS Settings")
    color: palette.window
    // Inject a host adapter around desktop.config.controller.SettingsController.
    property var settingsBackend
    property var preferences: ({})
    property string saveError: ""
    function reloadPreferences() {
        if (!settingsBackend) return
        preferences = settingsBackend.read()
        saveError = ""
    }
    function persist(path, value) {
        if (!settingsBackend) { saveError = qsTr("Settings service is unavailable."); return }
        let patch = ({}), cursor = patch, parts = path.split(".")
        for (let i=0; i<parts.length-1; ++i) { cursor[parts[i]] = ({}); cursor = cursor[parts[i]] }
        cursor[parts[parts.length-1]] = value
        try { preferences = settingsBackend.update(patch); saveError = "" }
        catch (error) {
            saveError = qsTr("Could not save settings. Your previous preferences are unchanged.")
            reloadPreferences()
        }
    }
    Component.onCompleted: reloadPreferences()
    ScrollView {
        anchors.fill: parent; clip: true
        ColumnLayout {
            width: Math.min(window.width-48,720)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 18
            Label { text: qsTr("Desktop preferences"); font.pixelSize: 26; font.bold: true
                Accessible.role: Accessible.Heading; Layout.topMargin: 24 }
            GroupBox {
                title: qsTr("Panel"); Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    Switch { text: qsTr("Enable desktop panel"); checked: !!preferences.panel?.enabled
                        Accessible.name: text; onToggled: persist("panel.enabled",checked) }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: qsTr("Panel position"); Layout.fillWidth: true }
                        ComboBox { model: [qsTr("Bottom"),qsTr("Top"),qsTr("Left"),qsTr("Right")]
                            Accessible.name: qsTr("Panel position")
                            currentIndex: ["bottom","top","left","right"].indexOf(preferences.panel?.edge ?? "bottom")
                            onActivated: persist("panel.edge",["bottom","top","left","right"][currentIndex]) }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: qsTr("Icon size"); Layout.fillWidth: true }
                        ComboBox { model: [24,32,40,48,56,64,72,80,88,96]
                            Accessible.name: qsTr("Panel icon size")
                            currentIndex: model.indexOf(preferences.panel?.icon_size ?? 48)
                            onActivated: persist("panel.icon_size",model[currentIndex]) }
                    }
                    Switch { text: qsTr("Automatically hide panel"); checked: !!preferences.panel?.auto_hide
                        Accessible.name: text; onToggled: persist("panel.auto_hide",checked) }
                }
            }
            GroupBox {
                title: qsTr("Assistant"); Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    Switch { text: qsTr("Show assistant panel"); checked: !!preferences.assistant?.enabled
                        Accessible.name: text; onToggled: persist("assistant.enabled",checked) }
                    Switch { text: qsTr("Show task progress"); checked: !!preferences.assistant?.show_task_progress
                        enabled: !!preferences.assistant?.enabled; Accessible.name: text
                        onToggled: persist("assistant.show_task_progress",checked) }
                }
            }
            GroupBox {
                title: qsTr("Accessibility"); Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    Switch { text: qsTr("Reduce motion"); checked: !!preferences.accessibility?.reduced_motion
                        Accessible.name: text; onToggled: persist("accessibility.reduced_motion",checked) }
                    Switch { text: qsTr("High contrast"); checked: !!preferences.accessibility?.high_contrast
                        Accessible.name: text; onToggled: persist("accessibility.high_contrast",checked) }
                }
            }
            Label { visible: saveError.length>0; text: saveError; color: palette.brightText
                wrapMode: Text.Wrap; Accessible.live: Accessible.Assertive; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                Button { text: qsTr("Restore defaults…"); Accessible.name: qsTr("Restore default desktop preferences")
                    onClicked: resetDialog.open() }
                Item { Layout.fillWidth: true }
                Button { text: qsTr("Reload"); onClicked: reloadPreferences() }
            }
        }
    }
    Dialog {
        id: resetDialog
        title: qsTr("Restore defaults?"); modal: true
        standardButtons: Dialog.Yes | Dialog.Cancel
        anchors.centerIn: parent
        Label { width: 360; wrapMode: Text.Wrap
            text: qsTr("This replaces your desktop preferences with safe defaults. This cannot be undone.") }
        onAccepted: {
            try { preferences=settingsBackend.reset(); saveError="" }
            catch (error) { saveError=qsTr("Could not restore defaults. Your previous preferences are unchanged.") }
        }
    }
}
