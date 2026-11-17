import QtQuick
import QtQuick.Controls.Basic
import "."

// Round icon button with a hover halo and a tooltip.
AbstractButton {
    id: control
    property string iconName: ""
    property real size: 36
    property string tip: ""
    property color iconColor: Theme.text
    property bool filledIcon: false
    property bool accentFill: false
    implicitWidth: size
    implicitHeight: size
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    scale: down ? 0.88 : (hovered ? 1.06 : 1.0)
    Behavior on scale { enabled: !Theme.reduceMotion; SpringAnimation { spring: 5; damping: 0.3 } }

    background: Rectangle {
        radius: width / 2
        gradient: control.accentFill ? accentGradient : null
        color: control.accentFill ? "transparent" : Qt.rgba(1, 1, 1, control.hovered ? 0.13 : 0.0)
        border.width: control.accentFill ? 0 : (control.hovered ? 1 : 0)
        border.color: Theme.glassBorder
        Behavior on color { ColorAnimation { duration: 150 } }
        Gradient {
            id: accentGradient
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Theme.accent }
            GradientStop { position: 1.0; color: Theme.accent2 }
        }
    }
    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            name: control.iconName
            size: control.size * 0.5
            color: control.iconColor
            filled: control.filledIcon
        }
    }
    ToolTip.visible: hovered && tip !== ""
    ToolTip.delay: 500
    ToolTip.text: tip
}
