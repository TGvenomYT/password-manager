import QtQuick
import QtQuick.Controls.Basic
import "."

Slider {
    id: control
    hoverEnabled: true
    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 6
        radius: 3
        color: Qt.rgba(1, 1, 1, 0.12)
        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 3
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Theme.accent3 }
                GradientStop { position: 1.0; color: Theme.accent }
            }
        }
    }
    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.pressed ? 24 : 20
        height: width
        radius: width / 2
        color: "white"
        border.width: 3
        border.color: Theme.accent
        Behavior on width { SpringAnimation { spring: 5; damping: 0.3 } }
    }
}
