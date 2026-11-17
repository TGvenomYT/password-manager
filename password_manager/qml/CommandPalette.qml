import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import "."

// ⌘K: find any password or run any action from the keyboard.
Popup {
    id: root
    property Item backdrop: null
    property var editor: null
    property var settings: null
    property var backup: null
    property var results: []
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round(parent.height * 0.13)
    width: 620
    padding: 14
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    readonly property var actions: [
        { label: "New Password", icon: "plus", run: function () { root.editor.openFor(null, "login") } },
        { label: "New Secure Note", icon: "note", run: function () { root.editor.openFor(null, "note") } },
        { label: "Check for Leaked Passwords", icon: "leak", run: function () { backend.setView("security"); backend.checkLeaks() } },
        { label: "Security Overview", icon: "shield", run: function () { backend.setView("security") } },
        { label: "Verification Codes", icon: "timer", run: function () { backend.setView("codes") } },
        { label: "Favorites", icon: "star", run: function () { backend.setView("favorites") } },
        { label: "Secure Notes", icon: "note", run: function () { backend.setView("notes") } },
        { label: "All Items", icon: "key", run: function () { backend.setView("all") } },
        { label: "Recently Deleted", icon: "trash", run: function () { backend.setView("trash") } },
        { label: "Settings", icon: "gear", run: function () { root.settings.open() } },
        { label: "Back Up Vault…", icon: "archive", run: function () { root.backup.openFor("export") } },
        { label: "Restore from Backup…", icon: "import", run: function () { root.backup.openFor("import") } },
        { label: "Theme: Aurora", icon: "palette", run: function () { backend.setTheme("aurora") } },
        { label: "Theme: Ocean", icon: "palette", run: function () { backend.setTheme("ocean") } },
        { label: "Theme: Sunset", icon: "palette", run: function () { backend.setTheme("sunset") } },
        { label: "Theme: Forest", icon: "palette", run: function () { backend.setTheme("forest") } },
        { label: "Lock Vault", icon: "lock", run: function () { backend.lock() } }
    ]

    function rebuild() {
        var q = query.text.trim().toLowerCase()
        var out = []
        var acts = actions.filter(function (a) { return !q || a.label.toLowerCase().indexOf(q) >= 0 })
        var entries = q ? backend.search(q) : []
        entries.forEach(function (e) { out.push({ type: "entry", label: e.name, detail: e.subtitle, id: e.id,
                                                  initial: e.initial, color: e.color }) })
        acts.forEach(function (a) { out.push({ type: "action", label: a.label, detail: "", icon: a.icon, action: a }) })
        results = out.slice(0, 9)
        list.currentIndex = results.length ? 0 : -1
    }
    function run(index) {
        var item = results[index]
        if (!item) return
        close()
        if (item.type === "entry") backend.reveal(item.id)
        else item.action.run()
    }
    onOpened: { query.text = ""; rebuild(); query.forceActiveFocus() }

    Overlay.modal: Item {
        MultiEffect {
            anchors.fill: parent
            source: root.backdrop
            visible: root.backdrop !== null
            blurEnabled: true; blur: 0.7; blurMax: 40
        }
        Rectangle { anchors.fill: parent; color: Qt.rgba(0.02, 0.02, 0.05, 0.45) }
    }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
        NumberAnimation { property: "scale"; from: 0.94; to: 1; duration: 300; easing.type: Easing.OutBack }
    }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 120 } }
    background: Rectangle {
        radius: 24
        color: Theme.glassStrong
        border.width: 1
        border.color: Theme.glassBorder
    }

    contentItem: Column {
        spacing: 10
        GlassField {
            id: query
            width: parent.width
            implicitHeight: 52
            font.pixelSize: 17
            iconName: "search"
            placeholderText: "Search passwords and actions"
            onTextChanged: root.rebuild()
            Keys.onUpPressed: list.currentIndex = Math.max(0, list.currentIndex - 1)
            Keys.onDownPressed: list.currentIndex = Math.min(root.results.length - 1, list.currentIndex + 1)
            Keys.onReturnPressed: root.run(list.currentIndex)
            Keys.onEnterPressed: root.run(list.currentIndex)
        }
        ListView {
            id: list
            width: parent.width
            height: Math.min(contentHeight, 9 * 50)
            model: root.results
            interactive: false
            highlightFollowsCurrentItem: false
            highlight: Rectangle {
                width: list.width; height: 48; radius: 13
                y: list.currentItem ? list.currentItem.y : 0
                Behavior on y { enabled: !Theme.reduceMotion; SpringAnimation { spring: 4; damping: 0.32 } }
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Theme.tint(Theme.accent, 0.45) }
                    GradientStop { position: 1.0; color: Theme.tint(Theme.accent2, 0.25) }
                }
            }
            delegate: Item {
                width: list.width
                height: 50
                Avatar {
                    visible: modelData.type === "entry"
                    x: 10; anchors.verticalCenter: parent.verticalCenter
                    size: 32; initial: modelData.initial || ""; tint: modelData.color || Theme.accent
                }
                Rectangle {
                    visible: modelData.type === "action"
                    x: 10; anchors.verticalCenter: parent.verticalCenter
                    width: 32; height: 32; radius: 10
                    color: Qt.rgba(1, 1, 1, 0.08)
                    Icon { anchors.centerIn: parent; name: modelData.icon || ""; size: 17; color: Theme.accent }
                }
                Column {
                    x: 54; anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 140
                    Text { width: parent.width; text: modelData.label; color: Theme.text; font.pixelSize: 15; font.weight: Font.Medium; elide: Text.ElideRight }
                    Text { visible: text !== ""; width: parent.width; text: modelData.detail || ""; color: Theme.tertiary; font.pixelSize: 12; elide: Text.ElideRight }
                }
                Text {
                    anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                    text: modelData.type === "entry" ? "Password" : "Action"
                    color: Theme.tertiary
                    font.pixelSize: 12
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onEntered: list.currentIndex = index
                    onClicked: root.run(index)
                }
            }
        }
        Text {
            visible: root.results.length === 0
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: "Nothing matches “" + query.text + "”."
            color: Theme.tertiary
            font.pixelSize: 14
            topPadding: 8; bottomPadding: 12
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignRight
            text: "↑↓ to move  ·  Return to open  ·  Esc to close"
            color: Theme.tertiary
            font.pixelSize: 11
        }
    }
}
