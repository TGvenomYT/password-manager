import QtQuick
import "."

// Two or more options with a pill that glides to the chosen one.
Rectangle {
    id: root
    property var options: []      // [{value, label}]
    property string value: ""
    signal picked(string value)
    implicitWidth: 240
    implicitHeight: 36
    radius: height / 2
    color: Qt.rgba(1, 1, 1, 0.07)
    border.width: 1
    border.color: Theme.glassBorder
    readonly property int index: Math.max(0, options.findIndex(function (o) { return o.value === value }))
    readonly property real segment: width / Math.max(1, options.length)

    Rectangle {
        y: 3
        height: parent.height - 6
        width: root.segment - 6
        x: 3 + root.index * root.segment
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Theme.accent }
            GradientStop { position: 1.0; color: Theme.accent2 }
        }
        Behavior on x { enabled: !Theme.reduceMotion; SpringAnimation { spring: 3.5; damping: 0.3 } }
    }
    Row {
        anchors.fill: parent
        Repeater {
            model: root.options
            delegate: Item {
                width: root.segment
                height: root.height
                Text {
                    anchors.centerIn: parent
                    text: modelData.label
                    color: modelData.value === root.value ? "white" : Theme.secondary
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.picked(modelData.value)
                }
            }
        }
    }
}
