import QtQuick
import "."

// A bar that fills like liquid, with a light ripple running through it.
Item {
    id: root
    property int score: -1   // -1 = empty, 0..4
    property bool showLabel: true
    implicitHeight: 18
    implicitWidth: 220

    Rectangle {
        id: track
        width: root.showLabel ? root.width - 92 : root.width
        height: 7
        anchors.verticalCenter: parent.verticalCenter
        radius: height / 2
        color: Qt.rgba(1, 1, 1, 0.08)
        clip: true
        Rectangle {
            id: fill
            height: parent.height
            radius: height / 2
            width: root.score < 0 ? 0 : parent.width * (root.score + 1) / 5
            color: Theme.strengthColor(root.score)
            Behavior on width { SpringAnimation { spring: 2.6; damping: 0.22 } }
            Behavior on color { ColorAnimation { duration: 300 } }
            Rectangle {  // ripple
                width: 40; height: parent.height
                radius: height / 2
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0) }
                    GradientStop { position: 0.5; color: Qt.rgba(1, 1, 1, 0.55) }
                    GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0) }
                }
                NumberAnimation on x {
                    running: !Theme.reduceMotion && fill.width > 0; loops: Animation.Infinite
                    from: -40; to: Math.max(fill.width, 60); duration: 1800; easing.type: Easing.InOutQuad
                }
            }
        }
    }
    Text {
        visible: root.showLabel
        anchors.left: track.right
        anchors.leftMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        text: root.score < 0 ? "" : ["Very weak", "Weak", "Fair", "Good", "Strong"][root.score]
        color: Theme.strengthColor(root.score)
        font.pixelSize: 13
        font.weight: Font.DemiBold
    }
}
