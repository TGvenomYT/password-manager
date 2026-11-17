import QtQuick
import QtQuick.Controls.Basic
import "."

// Text field on glass. secret = masked, with an eye button to reveal it (unless revealable is false).
TextField {
    id: control
    property string iconName: ""
    property bool secret: false
    property bool revealed: false
    property bool revealable: true
    property bool mono: false
    implicitHeight: 46
    color: Theme.text
    placeholderTextColor: Theme.tertiary
    selectionColor: Theme.tint(Theme.accent, 0.5)
    selectedTextColor: "white"
    font.pixelSize: 15
    font.family: mono ? Theme.mono : Qt.application.font.family
    echoMode: secret && !revealed ? TextInput.Password : TextInput.Normal
    passwordCharacter: "•"
    leftPadding: iconName ? 42 : 16
    rightPadding: secret ? 44 : 16
    verticalAlignment: TextInput.AlignVCenter

    background: Rectangle {
        radius: 13
        color: Qt.rgba(1, 1, 1, control.activeFocus ? 0.11 : (control.hovered ? 0.085 : 0.06))
        border.width: 1
        border.color: control.activeFocus ? Theme.accent : Theme.glassBorder
        Behavior on color { ColorAnimation { duration: 160 } }
        Behavior on border.color { ColorAnimation { duration: 160 } }
        Rectangle {  // soft outer glow while focused
            anchors.fill: parent
            anchors.margins: -4
            radius: parent.radius + 4
            color: "transparent"
            border.width: 4
            border.color: Theme.tint(Theme.accent, 0.22)
            opacity: control.activeFocus ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 200 } }
        }
    }

    Icon {
        visible: control.iconName !== ""
        name: control.iconName
        size: 17
        color: control.activeFocus ? Theme.text : Theme.tertiary
        anchors.left: parent.left
        anchors.leftMargin: 15
        anchors.verticalCenter: parent.verticalCenter
    }
    IconButton {
        visible: control.secret && control.revealable
        iconName: control.revealed ? "eyeOff" : "eye"
        size: 32
        anchors.right: parent.right
        anchors.rightMargin: 7
        anchors.verticalCenter: parent.verticalCenter
        tip: control.revealed ? "Hide" : "Show"
        onClicked: control.revealed = !control.revealed
    }
}
