import QtQuick
import QtQuick.Dialogs
import QtCore
import "."

// Encrypted backup: choose a backup password, then where to save (or which file to restore).
ModalCard {
    id: root
    cardWidth: 460
    property string mode: "export"   // export | import
    property string message: ""
    property bool messageIsError: false
    property bool done: false

    function openFor(newMode) {
        mode = newMode
        message = ""
        done = false
        open()
    }
    onOpened: { first.text = ""; second.text = ""; first.forceActiveFocus() }
    function proceed() {
        message = ""
        if (first.text.length < 8) { message = "Use at least 8 characters."; messageIsError = true; return }
        if (mode === "export" && first.text !== second.text) { message = "The passwords don't match."; messageIsError = true; return }
        (mode === "export" ? saveDialog : openDialog).open()
    }
    Connections {
        target: backend
        function onDialogMessage(text, isError) {
            if (root.opened) { root.message = text; root.messageIsError = isError; root.done = !isError }
        }
    }

    Row {
        spacing: 12
        Icon { name: root.mode === "export" ? "archive" : "import"; size: 24; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
        Text { text: root.mode === "export" ? "Back Up Vault" : "Restore from Backup"; color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
    }
    Text {
        width: 404
        wrapMode: Text.Wrap
        color: Theme.secondary
        font.pixelSize: 14
        lineHeight: 1.15
        text: root.mode === "export"
              ? "Saves every item, including 2FA keys, notes and password history, in one file encrypted with a backup password. Keep the password somewhere safe: without it the backup can't be opened."
              : "Adds the items from a .pmbackup file to this vault. Items you already have are skipped."
    }
    GlassField { id: first; width: 404; secret: true; iconName: "lock"; placeholderText: "Backup password"
                 onAccepted: root.mode === "export" ? second.forceActiveFocus() : root.proceed() }
    StrengthMeter { width: 404; visible: root.mode === "export" && first.text.length > 0; score: backend.strength(first.text) }
    GlassField { id: second; visible: root.mode === "export"; width: 404; secret: true; iconName: "lock"
                 placeholderText: "Confirm backup password"; onAccepted: root.proceed() }
    Text {
        width: 404
        visible: root.message !== ""
        text: root.message
        color: root.messageIsError ? Theme.danger : Theme.success
        font.pixelSize: 13
        wrapMode: Text.Wrap
    }
    Row {
        anchors.right: parent.right
        spacing: 10
        GlassButton { text: root.done ? "Done" : "Cancel"; primary: root.done; onClicked: root.close() }
        GlassButton {
            visible: !root.done
            text: root.mode === "export" ? "Choose Where to Save…" : "Choose Backup File…"
            primary: true
            loading: backend.busy
            onClicked: root.proceed()
        }
    }

    property FileDialog saveDialog: FileDialog {
        title: "Save Backup"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "pmbackup"
        nameFilters: ["Password Manager backups (*.pmbackup)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        selectedFile: currentFolder + "/Passwords " + new Date().toISOString().slice(0, 10) + ".pmbackup"
        onAccepted: backend.exportBackup(selectedFile.toString(), first.text, second.text)
    }
    property FileDialog openDialog: FileDialog {
        title: "Restore from Backup"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Password Manager backups (*.pmbackup)", "All files (*)"]
        onAccepted: backend.importBackup(selectedFile.toString(), first.text)
    }
}
