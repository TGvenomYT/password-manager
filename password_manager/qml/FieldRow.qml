import QtQuick
import "."

// One copyable row in the details card; click copies it with a ripple. A secret row (the password)
// is never shown: it's always the same dots, whatever the password, and clicking them copies it.
Item {
    id: row
    property string label: ""
    property string value: ""
    property string field: ""
    property bool secret: false
    property bool link: false
    property bool last: false
    property string trailing: ""
    property color trailingColor: Theme.secondary
    width: parent ? parent.width : 0
    height: 56
    clip: true

    Rectangle {
        anchors.fill: parent
        anchors.margins: 4
        radius: 12
        color: area.containsMouse ? Qt.rgba(1, 1, 1, 0.07) : "transparent"
        Behavior on color { ColorAnimation { duration: 160 } }
    }
    Rectangle {
        id: ripple
        property real cx: 0
        property real cy: 0
        width: 0; height: width; radius: width / 2
        x: cx - width / 2; y: cy - height / 2
        color: Theme.accent
        opacity: 0
    }
    ParallelAnimation {
        id: burst
        NumberAnimation { target: ripple; property: "width"; from: 0; to: row.width * 2.2; duration: 600; easing.type: Easing.OutCubic }
        NumberAnimation { target: ripple; property: "opacity"; from: 0.35; to: 0; duration: 600; easing.type: Easing.OutCubic }
    }
    Text {
        x: 20
        anchors.verticalCenter: parent.verticalCenter
        text: row.label
        color: Theme.secondary
        font.pixelSize: 14
    }
    Item {
        x: 150
        width: row.width - 150 - 110
        height: parent.height
        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            text: row.secret ? "\u2022".repeat(12) : row.value
            color: Theme.text
            font.pixelSize: 15
            font.letterSpacing: row.secret ? 1.5 : 0
            elide: Text.ElideRight
        }
    }
    Text {
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        text: area.containsMouse && !row.link ? "Copy" : row.trailing
        color: area.containsMouse && !row.link ? Theme.accent : row.trailingColor
        font.pixelSize: 13
        font.weight: Font.DemiBold
    }
    Rectangle {
        visible: !row.last
        anchors.bottom: parent.bottom
        x: 20
        width: parent.width - 20
        height: 1
        color: Qt.rgba(1, 1, 1, 0.07)
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: function (mouse) {
            ripple.cx = mouse.x
            ripple.cy = mouse.y
            if (!Theme.reduceMotion) burst.restart()
            backend.copyField(row.field)
        }
    }
    LinkText {   // above the row's MouseArea, so "Open" doesn't also copy
        visible: row.link
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        text: "Open ↗"
        font.pixelSize: 13
        onClicked: backend.openWebsite(row.value)
    }
}
