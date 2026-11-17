import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import "."

// Pill button. primary = gradient with a glow; destructive = rose tint.
Button {
    id: control
    property bool primary: false
    property bool destructive: false
    property string iconName: ""
    property bool loading: false
    implicitHeight: 40
    implicitWidth: Math.max(92, label.implicitWidth + (iconName ? 30 : 0) + 40)
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    font.pixelSize: 14
    font.weight: Font.DemiBold
    scale: down ? 0.95 : (hovered && enabled ? 1.03 : 1.0)
    opacity: enabled ? 1 : 0.45
    Behavior on scale { enabled: !Theme.reduceMotion; SpringAnimation { spring: 5; damping: 0.28 } }
    Behavior on opacity { NumberAnimation { duration: 160 } }

    contentItem: Item {
        implicitWidth: row.implicitWidth
        implicitHeight: row.implicitHeight
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 8
            opacity: control.loading ? 0 : 1
            Behavior on opacity { NumberAnimation { duration: 150 } }
            Icon {
                visible: control.iconName !== ""
                name: control.iconName
                size: 16
                anchors.verticalCenter: parent.verticalCenter
                color: label.color
            }
            Text {
                id: label
                text: control.text
                font: control.font
                color: control.destructive && !control.primary ? Theme.danger : "white"
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        Spinner {
            anchors.centerIn: parent
            size: 18
            visible: control.loading
            color: "white"
        }
    }

    background: Item {
        implicitHeight: 40
        Rectangle {
            id: fill
            anchors.fill: parent
            radius: height / 2
            visible: !control.primary
            color: control.destructive ? Qt.rgba(1, 0.42, 0.55, control.hovered ? 0.24 : 0.15)
                                       : Qt.rgba(1, 1, 1, control.hovered ? 0.15 : 0.09)
            border.width: 1
            border.color: control.destructive ? Qt.rgba(1, 0.42, 0.55, 0.45) : Theme.glassBorder
            Behavior on color { ColorAnimation { duration: 160 } }
        }
        Rectangle {
            id: grad
            anchors.fill: parent
            radius: height / 2
            visible: false
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: control.destructive ? "#FF5C7A" : Theme.accent }
                GradientStop { position: 1.0; color: control.destructive ? "#FF8A5C" : Theme.accent2 }
            }
        }
        MultiEffect {
            visible: control.primary
            anchors.fill: grad
            source: grad
            shadowEnabled: true
            shadowColor: control.destructive ? "#FF5C7A" : Theme.accent
            shadowBlur: 1.0
            shadowOpacity: control.hovered ? 0.85 : 0.45
            shadowVerticalOffset: 4
            brightness: control.hovered ? 0.08 : 0.0
            Behavior on shadowOpacity { NumberAnimation { duration: 200 } }
        }
        Rectangle {  // focus ring for keyboard users
            anchors.fill: parent
            anchors.margins: -3
            radius: height / 2
            color: "transparent"
            border.width: 2
            border.color: Theme.accent3
            visible: control.visualFocus
        }
    }
}
