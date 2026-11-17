import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Effects
import QtCore
import "."

Item {
    id: root
    GlassPanel {
        id: card
        anchors.centerIn: parent
        width: 520
        height: column.implicitHeight + 76
        radius: 32
        tint: Qt.rgba(1, 1, 1, 0.075)

        ColumnLayout {
            id: column
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 38 }
            spacing: 14

            Item {
                Layout.alignment: Qt.AlignHCenter
                implicitWidth: 76; implicitHeight: 76
                Rectangle {
                    id: halo
                    anchors.fill: parent
                    radius: width / 2
                    visible: false
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Theme.accent3 }
                        GradientStop { position: 1.0; color: Theme.accent }
                    }
                }
                MultiEffect {
                    anchors.fill: halo
                    source: halo
                    shadowEnabled: true
                    shadowColor: Theme.accent
                    shadowBlur: 1.0
                    shadowOpacity: 0.8
                }
                Icon { anchors.centerIn: parent; name: "key"; size: 36; lineWidth: 2.2; color: "white" }
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Save your recovery key"
                color: Theme.text
                font.pixelSize: 27
                font.weight: Font.Bold
            }
            Text {
                Layout.fillWidth: true
                text: backend.recoveryIntro + " Write it down, or keep it somewhere safe away from this computer."
                color: Theme.secondary
                font.pixelSize: 15
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                lineHeight: 1.15
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 6
                implicitHeight: 70
                radius: 18
                color: Qt.rgba(1, 1, 1, 0.06)
                border.width: 1
                border.color: Theme.tint(Theme.accent, 0.45)
                TextEdit {
                    anchors.centerIn: parent
                    text: backend.recoveryKey
                    readOnly: true
                    selectByMouse: true
                    color: "white"
                    selectionColor: Theme.tint(Theme.accent, 0.5)
                    font.family: Theme.mono
                    font.pixelSize: 23
                    font.weight: Font.Bold
                    font.letterSpacing: 1.2
                }
            }
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 10
                GlassButton { text: "Copy"; iconName: "copy"; onClicked: backend.copyRecoveryKey() }
                GlassButton { text: "Save as File…"; iconName: "export"; onClicked: saveDialog.open() }
            }
            Text {
                Layout.fillWidth: true
                visible: text !== ""
                text: backend.error
                color: Theme.danger
                font.pixelSize: 14
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 8
                spacing: 10
                GlassButton { Layout.fillWidth: true; text: "Remind Me Later"; onClicked: backend.skipRecoveryKey() }
                GlassButton {
                    Layout.fillWidth: true
                    primary: true
                    text: "I've Saved It"
                    iconName: "check"
                    loading: backend.busy
                    onClicked: backend.saveRecoveryKey()
                }
            }
        }
    }
    FileDialog {
        id: saveDialog
        title: "Save Recovery Key"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "txt"
        nameFilters: ["Text files (*.txt)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        selectedFile: currentFolder + "/Password Manager recovery key.txt"
        onAccepted: backend.saveRecoveryKeyFile(selectedFile.toString())
    }
    ParallelAnimation {
        running: true
        NumberAnimation { target: card; property: "opacity"; from: 0; to: 1; duration: 380 }
        NumberAnimation { target: card; property: "scale"; from: 0.92; to: 1; duration: 560; easing.type: Easing.OutBack }
    }
}
