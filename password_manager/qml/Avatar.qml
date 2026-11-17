import QtQuick
import "."

// The site's first letter on a glossy coloured tile.
Rectangle {
    id: root
    property string initial: "?"
    property color tint: Theme.accent
    property real size: 38
    width: size
    height: size
    radius: size * 0.3
    gradient: Gradient {
        GradientStop { position: 0.0; color: Qt.lighter(root.tint, 1.35) }
        GradientStop { position: 1.0; color: root.tint }
    }
    border.width: 1
    border.color: Qt.rgba(1, 1, 1, 0.28)
    Text {
        anchors.centerIn: parent
        text: root.initial
        color: "white"
        font.pixelSize: root.size * 0.44
        font.weight: Font.Bold
    }
}
