import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import "."

// A centred glass dialog over a blurred, dimmed copy of the window.
Popup {
    id: root
    property Item backdrop: null
    default property alias body: body.data
    property real cardWidth: 460
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: cardWidth
    modal: true
    focus: true
    padding: 28
    closePolicy: Popup.CloseOnEscape

    Overlay.modal: Item {
        MultiEffect {
            anchors.fill: parent
            source: root.backdrop
            visible: root.backdrop !== null
            blurEnabled: true
            blur: 0.8
            blurMax: 40
        }
        Rectangle { anchors.fill: parent; color: Qt.rgba(0.02, 0.02, 0.05, 0.5) }
    }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 180 }
        NumberAnimation { property: "scale"; from: 0.9; to: 1; duration: 320; easing.type: Easing.OutBack }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: 140 }
        NumberAnimation { property: "scale"; to: 0.96; duration: 140 }
    }
    background: Rectangle {
        radius: 24
        color: Theme.glassStrong
        border.width: 1
        border.color: Theme.glassBorder
        Rectangle {
            anchors.fill: parent; anchors.margins: 1; radius: 23
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.07) }
                GradientStop { position: 0.3; color: Qt.rgba(1, 1, 1, 0.0) }
            }
        }
    }
    contentItem: Column { id: body; spacing: 14 }
}
