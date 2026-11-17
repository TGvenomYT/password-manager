import QtQuick
import "."

Text {
    id: root
    signal clicked()
    color: area.containsMouse ? Qt.lighter(Theme.accent, 1.25) : Theme.accent
    font.pixelSize: 14
    font.weight: Font.Medium
    font.underline: area.containsMouse
    MouseArea {
        id: area
        anchors.fill: parent
        anchors.margins: -6
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
