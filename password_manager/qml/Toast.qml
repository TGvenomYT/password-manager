import QtQuick
import "."

// A glass pill that slides up from the bottom for a moment, optionally with an action like Undo.
Item {
    id: root
    width: pill.width
    height: pill.height
    property real shown: 0
    property var action: null
    opacity: shown
    visible: shown > 0
    transform: Translate { y: (1 - root.shown) * 24 }

    function show(message, actionLabel, action) {
        label.text = message
        button.text = actionLabel || ""
        root.action = action || null
        hideTimer.interval = action ? 5000 : 2400
        hideTimer.restart()
        appear.restart()
    }

    property real maxWidth: 640
    Rectangle {
        id: pill
        width: Math.min(row.implicitWidth, root.maxWidth) + 40
        height: Math.max(42, row.implicitHeight + 20)
        radius: 21
        color: Theme.glassStrong
        border.width: 1
        border.color: Theme.glassBorder
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 16
            Text {
                id: label
                width: Math.min(implicitWidth, root.maxWidth - (button.visible ? button.implicitWidth + 16 : 0))
                wrapMode: Text.Wrap
                anchors.verticalCenter: parent.verticalCenter
                color: Theme.text
                font.pixelSize: 14
                font.weight: Font.Medium
            }
            LinkText {
                id: button
                visible: text !== ""
                anchors.verticalCenter: parent.verticalCenter
                font.weight: Font.Bold
                onClicked: { var a = root.action; root.action = null; vanish.restart(); if (a) a() }
            }
        }
    }
    NumberAnimation { id: appear; target: root; property: "shown"; to: 1; duration: 320; easing.type: Easing.OutBack }
    NumberAnimation { id: vanish; target: root; property: "shown"; to: 0; duration: 260; easing.type: Easing.InCubic }
    Timer { id: hideTimer; interval: 2400; onTriggered: vanish.restart() }
}
