import QtQuick
import QtQuick.Controls.Basic
import "."

// A switch whose knob stretches like a droplet while it slides.
Switch {
    id: control
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45
    spacing: 10
    font.pixelSize: 14
    indicator: Rectangle {
        id: track
        implicitWidth: 44
        implicitHeight: 26
        x: control.leftPadding
        anchors.verticalCenter: parent.verticalCenter
        radius: height / 2
        color: Qt.rgba(1, 1, 1, 0.12)
        border.width: 1
        border.color: Theme.glassBorder
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            opacity: control.checked ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 220 } }
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Theme.accent }
                GradientStop { position: 1.0; color: Theme.accent2 }
            }
        }
        Rectangle {
            id: knob
            property real stretch: 0
            width: 20 + stretch
            height: 20
            radius: 10
            y: 3
            x: control.checked ? track.width - width - 3 : 3
            color: "white"
            Behavior on x { enabled: !Theme.reduceMotion; SpringAnimation { spring: 4; damping: 0.32 } }
            SequentialAnimation {
                id: squish
                NumberAnimation { target: knob; property: "stretch"; to: 8; duration: 90; easing.type: Easing.OutQuad }
                NumberAnimation { target: knob; property: "stretch"; to: 0; duration: 260; easing.type: Easing.OutBack }
            }
        }
    }
    onToggled: if (!Theme.reduceMotion) squish.restart()
    contentItem: Text {
        text: control.text
        font: control.font
        color: Theme.text
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
    }
}
