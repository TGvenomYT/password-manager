import QtQuick
import QtQuick.Layouts
import "."

Item {
    id: root
    property Item backdrop: null
    property real topInset: 0

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        Sidebar {
            id: sidebar
            Layout.preferredWidth: 240
            Layout.fillHeight: true
            topInset: root.topInset
            onSettingsRequested: settings.open()
            opacity: 0
            transform: Translate { id: sidebarShift }
        }
        EntryList {
            id: list
            visible: backend.view !== "security"
            Layout.preferredWidth: 350
            Layout.fillHeight: true
            onAddRequested: function (kind) { editor.openFor(null, kind) }
            onEditRequested: if (backend.selected.id !== undefined && !backend.selected.deleted) editor.openFor(backend.selected)
            onEmptyRequested: confirm.ask("Empty Recently Deleted?", "Everything in Recently Deleted will be deleted "
                                          + "permanently. You can't undo this.", "Empty", function () { backend.emptyTrash() })
            opacity: 0
            transform: Translate { id: listShift }
        }
        SecurityDashboard {
            id: dashboard
            visible: backend.view === "security"
            Layout.fillWidth: true
            Layout.fillHeight: true
            onVisibleChanged: if (visible && !Theme.reduceMotion) dashIn.restart()
            transform: Translate { id: dashShift }
            ParallelAnimation {
                id: dashIn
                NumberAnimation { target: dashboard; property: "opacity"; from: 0; to: 1; duration: 320 }
                NumberAnimation { target: dashShift; property: "y"; from: 20; to: 0; duration: 480; easing.type: Easing.OutBack }
            }
        }
        Item {
            id: right
            visible: backend.view !== "security"
            Layout.fillWidth: true
            Layout.fillHeight: true
            opacity: 0
            transform: Translate { id: rightShift }
            DetailPane {
                anchors.fill: parent
                opacity: 1 - editor.shown
                enabled: !editor.open
                visible: opacity > 0.01
                confirm: confirm
                onEditRequested: editor.openFor(backend.selected)
            }
            Editor {
                id: editor
                objectName: "editor"
                anchors.fill: parent
                confirm: confirm
            }
        }
    }

    // panes float in one after another
    SequentialAnimation {
        running: true
        ParallelAnimation {
            NumberAnimation { target: sidebar; property: "opacity"; to: 1; duration: 320 }
            NumberAnimation { target: sidebarShift; property: "y"; from: 24; to: 0; duration: 520; easing.type: Easing.OutBack }
        }
    }
    SequentialAnimation {
        running: true
        PauseAnimation { duration: 90 }
        ParallelAnimation {
            NumberAnimation { target: list; property: "opacity"; to: 1; duration: 320 }
            NumberAnimation { target: listShift; property: "y"; from: 24; to: 0; duration: 520; easing.type: Easing.OutBack }
        }
    }
    SequentialAnimation {
        running: true
        PauseAnimation { duration: 180 }
        ParallelAnimation {
            NumberAnimation { target: right; property: "opacity"; to: 1; duration: 320 }
            NumberAnimation { target: rightShift; property: "y"; from: 24; to: 0; duration: 520; easing.type: Easing.OutBack }
        }
    }

    SettingsDialog { id: settings; objectName: "settings"; backdrop: root.backdrop; confirm: confirm
                     changePassword: changePassword; backupDialog: backupDialog }
    BackupDialog { id: backupDialog; objectName: "backupDialog"; backdrop: root.backdrop }
    CommandPalette { id: palette; objectName: "palette"; backdrop: root.backdrop; editor: editor; settings: settings; backup: backupDialog }
    ChangePasswordDialog { id: changePassword; backdrop: root.backdrop }
    ConfirmDialog { id: confirm; backdrop: root.backdrop }

    Shortcut { sequences: [StandardKey.New]; onActivated: editor.openFor(null, backend.view === "notes" ? "note" : "login") }
    Shortcut { sequence: "Ctrl+K"; onActivated: palette.opened ? palette.close() : palette.open() }
    Shortcut { sequences: [StandardKey.Find]; onActivated: list.focusSearch() }
    Shortcut { sequence: "Ctrl+L"; onActivated: backend.lock() }
    Shortcut { sequence: "Ctrl+,"; onActivated: settings.open() }
}
