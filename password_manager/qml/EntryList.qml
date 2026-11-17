import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

GlassPanel {
    id: root
    signal addRequested(string kind)
    signal editRequested()
    property bool cascade: true
    property string lastView: ""

    function focusSearch() { search.forceActiveFocus(); search.selectAll() }
    function syncIndex() {
        var items = backend.items
        for (var i = 0; i < items.length; i++) {
            if (items[i].id === backend.selectedId) { list.currentIndex = i; return }
        }
        list.currentIndex = -1
    }
    Connections {
        target: backend
        function onListChanged() {
            if (backend.view !== root.lastView) {
                root.lastView = backend.view
                root.cascade = true
                cascadeOff.restart()
            }
            Qt.callLater(root.syncIndex)
        }
        function onSelectedChanged() { root.syncIndex() }
    }
    Timer { id: cascadeOff; interval: 700; onTriggered: root.cascade = false }
    Component.onCompleted: { lastView = backend.view; cascadeOff.start() }

    RowLayout {
        id: bar
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
        spacing: 10
        GlassField {
            id: search
            Layout.fillWidth: true
            implicitHeight: 42
            iconName: "search"
            placeholderText: "Search"
            text: backend.query
            onTextEdited: backend.setQuery(text)
            Keys.onDownPressed: list.forceActiveFocus()
            Keys.onEscapePressed: { text = ""; backend.setQuery("") }
        }
        IconButton {
            id: add
            size: 42
            iconName: backend.view === "trash" ? "trash" : "plus"
            iconColor: "white"
            accentFill: true
            tip: backend.view === "trash" ? "Empty Recently Deleted" : backend.view === "notes" ? "New secure note" : "New password"
            rotation: hovered && backend.view !== "trash" ? 90 : 0
            Behavior on rotation { enabled: !Theme.reduceMotion; SpringAnimation { spring: 3; damping: 0.3 } }
            onClicked: backend.view === "trash" ? root.emptyRequested()
                                                : root.addRequested(backend.view === "notes" ? "note" : "login")
        }
    }
    signal emptyRequested()

    Column {
        id: heading
        anchors { left: parent.left; right: parent.right; top: bar.bottom; topMargin: 18; leftMargin: 20; rightMargin: 56 }
        spacing: 2
        Text { width: parent.width; text: backend.viewTitle; color: Theme.text; font.pixelSize: 22; font.weight: Font.Bold; elide: Text.ElideRight }
        Text {
            text: list.count + " item" + (list.count === 1 ? "" : "s") + (backend.query.trim() !== "" ? " found" : "")
                  + "  \u00b7  " + ({ "name": "by name", "modified": "recently edited", "created": "recently added" })[backend.sort]
            color: Theme.tertiary
            font.pixelSize: 13
        }
    }
    IconButton {
        id: sortButton
        anchors { right: parent.right; rightMargin: 14; verticalCenter: heading.verticalCenter }
        iconName: "sort"
        tip: "Sort"
        onClicked: sortMenu.open()
        Menu {
            id: sortMenu
            y: sortButton.height + 6
            x: sortButton.width - width
            padding: 6
            enter: Transition {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 }
                NumberAnimation { property: "scale"; from: 0.92; to: 1; duration: 220; easing.type: Easing.OutBack }
            }
            background: Rectangle {
                implicitWidth: 200
                radius: 14
                color: Theme.glassStrong
                border.width: 1
                border.color: Theme.glassBorder
            }
            Repeater {
                model: [{ key: "name", label: "Name" }, { key: "modified", label: "Recently Edited" },
                        { key: "created", label: "Recently Added" }]
                delegate: MenuItem {
                    id: menuItem
                    text: modelData.label
                    onTriggered: backend.setSort(modelData.key)
                    contentItem: Row {
                        spacing: 10
                        Icon { name: "check"; size: 14; color: Theme.accent; opacity: backend.sort === modelData.key ? 1 : 0
                               anchors.verticalCenter: parent.verticalCenter }
                        Text { text: menuItem.text; color: Theme.text; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                    }
                    background: Rectangle { radius: 9; color: menuItem.highlighted ? Theme.tint(Theme.accent, 0.3) : "transparent" }
                }
            }
        }
    }

    ListView {
        id: list
        anchors { left: parent.left; right: parent.right; top: heading.bottom; bottom: parent.bottom; margins: 10; topMargin: 12 }
        clip: true
        model: backend.items
        spacing: 2
        focus: true
        keyNavigationEnabled: false
        highlightFollowsCurrentItem: false
        boundsBehavior: Flickable.DragOverBounds
        function step(delta) {
            var items = backend.items
            if (items.length === 0) return
            var next = Math.max(0, Math.min(items.length - 1, (currentIndex < 0 ? 0 : currentIndex + delta)))
            currentIndex = next
            positionViewAtIndex(next, ListView.Contain)
            backend.select(items[next].id)
        }
        Keys.onPressed: function (event) {
            if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
                step(event.key === Qt.Key_Up ? -1 : 1)
                event.accepted = true
            } else if (event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace) {
                if (backend.view !== "trash") backend.trashSelected()
                event.accepted = true
            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                root.editRequested()
                event.accepted = true
            } else if (event.matches(StandardKey.Copy)) {
                backend.copyField("password")
                event.accepted = true
            }
        }
        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
            visible: list.contentHeight > list.height
            contentItem: Rectangle { implicitWidth: 5; radius: 3; color: Qt.rgba(1, 1, 1, 0.25) }
        }

        highlight: Rectangle {
            width: list.width
            height: 62
            radius: 15
            y: list.currentItem ? list.currentItem.y : 0
            visible: list.currentIndex >= 0
            Behavior on y { enabled: !Theme.reduceMotion; SpringAnimation { spring: 3.4; damping: 0.3 } }
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Theme.tint(Theme.accent, list.activeFocus ? 0.50 : 0.32) }
                GradientStop { position: 1.0; color: Theme.tint(Theme.accent2, list.activeFocus ? 0.32 : 0.18) }
            }
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.20)
        }

        delegate: Item {
            id: row
            width: list.width
            height: 62
            opacity: 1
            Component.onCompleted: {
                if (root.cascade && !Theme.reduceMotion) {
                    opacity = 0
                    slide.x = -14
                    appear.start()
                }
            }
            transform: Translate { id: slide }
            SequentialAnimation {
                id: appear
                PauseAnimation { duration: Math.min(index, 12) * 32 }
                ParallelAnimation {
                    NumberAnimation { target: row; property: "opacity"; to: 1; duration: 260 }
                    NumberAnimation { target: slide; property: "x"; to: 0; duration: 420; easing.type: Easing.OutBack }
                }
            }
            Rectangle {
                anchors.fill: parent
                radius: 15
                color: hover.containsMouse && !row.ListView.isCurrentItem ? Theme.hover : "transparent"
                Behavior on color { ColorAnimation { duration: 140 } }
            }
            Avatar {
                x: 12
                anchors.verticalCenter: parent.verticalCenter
                size: 40
                initial: modelData.initial
                tint: modelData.color
            }
            Column {
                x: 66
                width: parent.width - 66 - 36
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    width: parent.width
                    text: modelData.name
                    color: Theme.text
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Row {
                    width: parent.width
                    spacing: 6
                    Icon { visible: modelData.kind === "note"; name: "note"; size: 13; color: Theme.secondary
                           anchors.verticalCenter: parent.verticalCenter }
                    Text {
                        width: parent.width - 40
                        text: modelData.kind === "note" ? "Secure note" : modelData.subtitle
                        color: Theme.secondary
                        font.pixelSize: 13
                        elide: Text.ElideRight
                    }
                }
            }
            Icon {
                visible: modelData.favorite
                anchors.right: parent.right
                anchors.rightMargin: 14
                y: 14
                name: "star"
                filled: true
                size: 13
                lineWidth: 1
                color: Theme.star
            }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 14
                y: 36
                spacing: 6
                Icon { visible: modelData.hasTotp; name: "timer"; size: 13; color: Theme.accent3 }
                Rectangle {
                    visible: modelData.pwned || ((modelData.weak || modelData.reused)
                             && ["weak", "reused", "trash"].indexOf(backend.view) < 0)
                    anchors.verticalCenter: parent.verticalCenter
                    width: 8; height: 8; radius: 4
                    color: modelData.pwned ? Theme.danger : Theme.warning
                }
            }
            MouseArea {
                id: hover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: { list.currentIndex = index; backend.select(modelData.id); list.forceActiveFocus() }
                onDoubleClicked: root.editRequested()
            }
        }
    }

    Column {
        visible: list.count === 0
        anchors.centerIn: list
        width: list.width - 40
        spacing: 10
        Icon {
            anchors.horizontalCenter: parent.horizontalCenter
            name: backend.query.trim() !== "" ? "search" : ({ "all": "key", "favorites": "star", "codes": "timer",
                  "notes": "note", "weak": "shield", "reused": "shield", "old": "clock", "pwned": "leak",
                  "trash": "trash", "security": "shield" })[backend.view] || "key"
            size: 44
            lineWidth: 1.4
            color: Theme.tertiary
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: backend.query.trim() !== "" ? "No Results" : ({ "all": "No Passwords Yet", "favorites": "No Favorites",
                  "codes": "No Verification Codes", "notes": "No Secure Notes", "weak": "No Weak Passwords",
                  "reused": "No Reused Passwords", "old": "No Old Passwords", "pwned": "No Leaked Passwords",
                  "trash": "Nothing Deleted" })[backend.view] || ""
            color: Theme.secondary
            font.pixelSize: 16
            font.weight: Font.DemiBold
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            text: backend.query.trim() !== "" ? "Nothing matches “" + backend.query.trim() + "”."
                : ({ "all": "Click + to add your first password, or import them in Settings.",
                     "favorites": "Click the star on a password to keep it here.",
                     "codes": "Add a site's 2FA secret key to an entry and its 6-digit codes appear here.",
                     "notes": "Keep PINs, licence keys and recovery codes here. Click + to write one.",
                     "weak": "None of your passwords are easy to guess.",
                     "reused": "Every account has its own password.",
                     "old": "Every password was changed within the last year.",
                     "pwned": backend.security.checked ? "None of your passwords appear in known leaks."
                              : "Run a leak check from the Security overview.",
                     "trash": "Deleted passwords stay here for 30 days." })[backend.view] || ""
            color: Theme.tertiary
            font.pixelSize: 13
        }
    }
}
