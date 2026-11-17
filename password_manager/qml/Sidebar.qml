import QtQuick
import QtQuick.Layouts
import "."

GlassPanel {
    id: root
    signal settingsRequested()
    property real topInset: 0
    readonly property var nav: [
        { key: "all", label: "All Items", icon: "key", header: "" },
        { key: "favorites", label: "Favorites", icon: "star", header: "" },
        { key: "codes", label: "Verification Codes", icon: "timer", header: "" },
        { key: "notes", label: "Secure Notes", icon: "note", header: "" },
        { key: "security", label: "Overview", icon: "shield", header: "Security" },
        { key: "weak", label: "Weak", icon: "warning", header: "" },
        { key: "reused", label: "Reused", icon: "reused", header: "" },
        { key: "old", label: "Old", icon: "clock", header: "" },
        { key: "pwned", label: "Leaked", icon: "leak", header: "" },
        { key: "trash", label: "Recently Deleted", icon: "trash", header: " " }
    ]
    readonly property int rowHeight: 36
    readonly property int current: Math.max(0, nav.findIndex(function (n) { return n.key === backend.view }))

    component NavItem: Item {
        id: item
        property string label: ""
        property string iconName: ""
        property int count: -1
        property bool alert: false
        property bool selected: false
        property string header: ""
        readonly property real headerHeight: header === "" ? 0 : (header.trim() === "" ? 14 : 30)
        signal clicked()
        width: parent ? parent.width : 0
        height: headerHeight + root.rowHeight
        Text {
            visible: item.header.trim() !== ""
            text: item.header.toUpperCase()
            color: Theme.tertiary
            font.pixelSize: 11
            font.weight: Font.Bold
            font.letterSpacing: 1.2
            x: 14
            y: 10
        }
        Rectangle {
            y: item.headerHeight
            width: parent.width
            height: root.rowHeight
            radius: 11
            color: area.containsMouse && !item.selected ? Theme.hover : "transparent"
            Behavior on color { ColorAnimation { duration: 140 } }
        }
        Icon {
            x: 14
            y: item.headerHeight + (root.rowHeight - 18) / 2
            name: item.iconName
            size: 18
            color: item.selected ? "white" : Theme.accent
            Behavior on color { ColorAnimation { duration: 200 } }
        }
        Text {
            x: 44
            y: item.headerHeight
            height: root.rowHeight
            verticalAlignment: Text.AlignVCenter
            text: item.label
            color: Theme.text
            font.pixelSize: 14
            font.weight: item.selected ? Font.DemiBold : Font.Normal
        }
        Rectangle {
            visible: item.count > 0
            anchors.right: parent.right
            anchors.rightMargin: 10
            y: item.headerHeight + (root.rowHeight - 20) / 2
            height: 20
            width: Math.max(26, countText.implicitWidth + 14)
            radius: 10
            color: item.alert ? Qt.rgba(1, 0.7, 0.36, 0.22) : Qt.rgba(1, 1, 1, 0.10)
            Text {
                id: countText
                anchors.centerIn: parent
                text: item.count
                color: item.alert ? Theme.warning : Theme.secondary
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }
        }
        MouseArea {
            id: area
            y: item.headerHeight
            width: parent.width
            height: root.rowHeight
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: item.clicked()
        }
    }

    Row {
        id: brand
        x: 18
        y: 20 + root.topInset
        spacing: 12
        LiquidLock { size: 38; animate: false }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            Text { text: "Passwords"; color: Theme.text; font.pixelSize: 17; font.weight: Font.Bold }
            Text {
                text: (backend.counts.all || 0) + " saved"
                color: Theme.tertiary
                font.pixelSize: 12
            }
        }
    }

    Item {
        id: navBox
        anchors { left: parent.left; right: parent.right; top: brand.bottom; topMargin: 16; leftMargin: 10; rightMargin: 10 }
        height: navColumn.height

        Rectangle {
            id: pill
            readonly property Item target: repeater.count > root.current ? repeater.itemAt(root.current) : null
            width: parent.width
            height: root.rowHeight
            radius: 11
            y: target ? target.y + target.headerHeight : 0
            Behavior on y { enabled: !Theme.reduceMotion; SpringAnimation { spring: 3.2; damping: 0.28 } }
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Theme.tint(Theme.accent, 0.55) }
                GradientStop { position: 1.0; color: Theme.tint(Theme.accent2, 0.38) }
            }
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.22)
            // a little squash and stretch whenever it moves
            onYChanged: if (!Theme.reduceMotion && !stretch.running) stretch.restart()
            transform: Scale { id: pillScale; origin.y: root.rowHeight / 2; yScale: 1 }
            SequentialAnimation {
                id: stretch
                NumberAnimation { target: pillScale; property: "yScale"; to: 1.18; duration: 110; easing.type: Easing.OutQuad }
                NumberAnimation { target: pillScale; property: "yScale"; to: 1.0; duration: 380; easing.type: Easing.OutElastic }
            }
        }
        Column {
            id: navColumn
            width: parent.width
            Repeater {
                id: repeater
                model: root.nav
                delegate: NavItem {
                    label: modelData.label
                    iconName: modelData.icon
                    header: modelData.header
                    selected: index === root.current
                    count: modelData.key === "security" ? -1
                           : (backend.counts[modelData.key] !== undefined ? backend.counts[modelData.key] : -1)
                    alert: ["weak", "reused", "old", "pwned"].indexOf(modelData.key) >= 0 && count > 0
                    onClicked: backend.setView(modelData.key)
                }
            }
        }
    }

    Column {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 10; bottomMargin: 14 }
        NavItem { label: "Settings"; iconName: "gear"; onClicked: root.settingsRequested() }
        NavItem { label: "Lock"; iconName: "lock"; onClicked: backend.lock() }
    }
}
