import QtQuick
import "."

// A frosted pane: translucent fill, a hairline border and a sheen along the top edge.
Item {
    id: root
    property real radius: Theme.radius
    property color tint: Theme.glass
    property color borderColor: Theme.glassBorder
    default property alias content: inner.data

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.tint
        border.width: 1
        border.color: root.borderColor
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: root.radius - 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.085) }
            GradientStop { position: 0.28; color: Qt.rgba(1, 1, 1, 0.0) }
        }
    }
    Item { id: inner; anchors.fill: parent }
}
