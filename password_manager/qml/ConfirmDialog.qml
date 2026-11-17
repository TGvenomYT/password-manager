import QtQuick
import "."

ModalCard {
    id: root
    property string title: ""
    property string message: ""
    property string confirmText: "OK"
    property bool destructive: true
    property var action: null
    cardWidth: 420

    function ask(title, message, confirmText, action) {
        root.title = title
        root.message = message
        root.confirmText = confirmText
        root.action = action
        root.open()
    }

    Text { text: root.title; color: Theme.text; font.pixelSize: 19; font.weight: Font.Bold; width: 364; wrapMode: Text.Wrap }
    Text { text: root.message; color: Theme.secondary; font.pixelSize: 14; width: 364; wrapMode: Text.Wrap; lineHeight: 1.15 }
    Item { width: 1; height: 4 }
    Row {
        anchors.right: parent.right
        spacing: 10
        GlassButton { text: "Cancel"; onClicked: root.close() }
        GlassButton {
            text: root.confirmText
            primary: true
            destructive: root.destructive
            onClicked: { root.close(); if (root.action) root.action() }
        }
    }
}
