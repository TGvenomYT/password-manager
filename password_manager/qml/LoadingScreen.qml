import QtQuick
import "."

Item {
    Column {
        anchors.centerIn: parent
        spacing: 22
        LiquidLock { anchors.horizontalCenter: parent.horizontalCenter; size: 104; working: true }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Opening your vault…"
            color: Theme.secondary
            font.pixelSize: 16
        }
    }
}
