import QtQuick
import QtQuick.Layouts
import "."

ModalCard {
    id: root
    cardWidth: 440
    property string message: ""
    onOpened: { current.text = ""; next.text = ""; confirmField.text = ""; message = ""; current.forceActiveFocus() }
    Connections {
        target: backend
        function onDialogMessage(text, isError) { if (root.opened) root.message = text }
        function onPasswordChanged() { if (root.opened) root.close() }
    }
    Text { text: "Change Master Password"; color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
    Text { text: "Your recovery key keeps working after the change."; color: Theme.secondary; font.pixelSize: 14 }
    GlassField { id: current; width: 384; secret: true; iconName: "lock"; placeholderText: "Current master password"; onAccepted: next.forceActiveFocus() }
    GlassField { id: next; width: 384; secret: true; iconName: "lock"; placeholderText: "New master password"; onAccepted: confirmField.forceActiveFocus() }
    StrengthMeter { width: 384; visible: next.text.length > 0; score: backend.strength(next.text) }
    GlassField { id: confirmField; width: 384; secret: true; iconName: "lock"; placeholderText: "Confirm new master password"; onAccepted: go() }
    Text { width: 384; visible: root.message !== ""; text: root.message; color: Theme.danger; font.pixelSize: 13; wrapMode: Text.Wrap }
    Row {
        anchors.right: parent.right
        spacing: 10
        GlassButton { text: "Cancel"; onClicked: root.close() }
        GlassButton { text: "Change Password"; primary: true; loading: backend.busy; onClicked: go() }
    }
    function go() { root.message = ""; backend.changeMasterPassword(current.text, next.text, confirmField.text) }
}
