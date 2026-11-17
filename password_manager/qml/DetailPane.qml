import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import "."

GlassPanel {
    id: root
    signal editRequested()
    property var confirm: null
    readonly property var e: backend.selected
    readonly property bool has: e.id !== undefined

    component Card: Rectangle {
        width: parent ? parent.width : 0
        radius: 18
        color: Theme.glassInner
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.08)
    }
    component Notice: Card {
        id: notice
        property string iconName: ""
        property color tint: Theme.warning
        property string title: ""
        property string message: ""
        height: noticeText.implicitHeight + 64
        border.color: Qt.rgba(tint.r, tint.g, tint.b, 0.35)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.rgba(notice.tint.r, notice.tint.g, notice.tint.b, 0.14) }
            GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0.03) }
        }
        Icon { x: 20; y: 20; name: notice.iconName; size: 20; color: notice.tint }
        Text { x: 52; y: 19; text: notice.title; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
        Text {
            id: noticeText
            x: 52; y: 42
            width: notice.width - 72
            text: notice.message
            color: Theme.secondary
            font.pixelSize: 13
            wrapMode: Text.Wrap
            lineHeight: 1.15
        }
    }

    Column {
        visible: !root.has
        anchors.centerIn: parent
        spacing: 14
        LiquidLock { anchors.horizontalCenter: parent.horizontalCenter; size: 72; animate: !Theme.reduceMotion }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "No Password Selected"
            color: Theme.tertiary
            font.pixelSize: 17
            font.weight: Font.DemiBold
        }
    }

    Flickable {
        id: flick
        visible: root.has
        anchors.fill: parent
        anchors.margins: 30
        contentHeight: content.height + 20
        clip: true
        boundsBehavior: Flickable.DragOverBounds
        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
            visible: flick.contentHeight > flick.height
            contentItem: Rectangle { implicitWidth: 5; radius: 3; color: Qt.rgba(1, 1, 1, 0.25) }
        }

        Column {
            id: content
            width: Math.min(flick.width, 720)
            spacing: 16
            transform: Translate { id: enterShift }

            Item {
                width: parent.width
                height: 92
                Rectangle {
                    id: avatarGlow
                    x: 8; y: 8
                    width: 76; height: 76; radius: 38
                    color: root.has ? root.e.color : "transparent"
                    visible: false
                }
                MultiEffect {
                    anchors.fill: avatarGlow
                    source: avatarGlow
                    blurEnabled: true; blur: 1.0; blurMax: 48
                    autoPaddingEnabled: true
                    opacity: 0.7
                }
                Avatar {
                    id: avatar
                    size: 80
                    initial: root.has ? root.e.initial : ""
                    tint: root.has ? root.e.color : Theme.accent
                }
                Column {
                    x: 104
                    width: parent.width - 104 - actions.width - 12
                    anchors.verticalCenter: avatar.verticalCenter
                    spacing: 4
                    Text {
                        width: parent.width
                        text: root.has ? root.e.name : ""
                        color: Theme.text
                        font.pixelSize: 30
                        font.weight: Font.Bold
                        elide: Text.ElideRight
                    }
                    Text {
                        width: parent.width
                        text: root.has ? (root.e.kind === "note" ? "Secure note" : (root.e.host || root.e.username)) : ""
                        color: Theme.secondary
                        font.pixelSize: 15
                        elide: Text.ElideRight
                    }
                }
                Row {
                    id: actions
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: 6
                    IconButton {
                        id: star
                        visible: root.has && !root.e.deleted
                        iconName: "star"
                        filledIcon: root.has && root.e.favorite
                        iconColor: root.has && root.e.favorite ? Theme.star : Theme.secondary
                        tip: root.has && root.e.favorite ? "Remove from Favorites" : "Add to Favorites"
                        onClicked: { pop.restart(); backend.toggleFavorite() }
                        SequentialAnimation {
                            id: pop
                            NumberAnimation { target: star; property: "scale"; to: 1.45; duration: 110; easing.type: Easing.OutQuad }
                            NumberAnimation { target: star; property: "scale"; to: 1.0; duration: 420; easing.type: Easing.OutElastic }
                        }
                    }
                    IconButton {
                        visible: root.has && !root.e.deleted && root.e.decryptable
                        iconName: "edit"; tip: "Edit"
                        onClicked: root.editRequested()
                    }
                    IconButton {
                        visible: root.has && !root.e.deleted
                        iconName: "trash"; iconColor: Theme.danger; tip: "Delete"
                        onClicked: backend.trashSelected()
                    }
                    IconButton {
                        visible: root.has && root.e.deleted
                        iconName: "restore"; tip: "Restore"
                        onClicked: backend.restoreSelected()
                    }
                    IconButton {
                        visible: root.has && root.e.deleted
                        iconName: "trash"; iconColor: Theme.danger; tip: "Delete now"
                        onClicked: root.confirm.ask("Delete permanently?", "“" + root.e.name
                                   + "” will be deleted right away. You can't undo this.", "Delete",
                                   function () { backend.deleteSelectedNow() })
                    }
                }
            }

            Notice {
                visible: root.has && root.e.deleted
                iconName: "trash"
                tint: Theme.secondary
                title: "In Recently Deleted"
                message: root.has ? "This password will be deleted permanently in " + root.e.daysLeft + " day"
                                    + (root.e.daysLeft === 1 ? "" : "s") + ". Restore it to use it again." : ""
            }

            Card {
                visible: root.has && (root.e.kind !== "note" || root.e.hasPassword)
                height: fields.height
                Column {
                    id: fields
                    width: parent.width
                    FieldRow {
                        visible: root.has && root.e.username !== ""
                        label: "User Name"; field: "username"
                        value: root.has ? root.e.username : ""
                    }
                    FieldRow {
                        objectName: "passwordRow"
                        visible: root.has && (root.e.kind !== "note" || root.e.hasPassword)
                        label: "Password"; field: "password"; secret: root.has && root.e.decryptable
                        value: root.has && !root.e.decryptable ? "Can't be decrypted" : ""  // never the password
                        trailing: root.has && root.e.decryptable ? root.e.strengthLabel : ""
                        trailingColor: Theme.strengthColor(root.has ? root.e.strength : -1)
                        last: !(root.has && root.e.website !== "")
                    }
                    FieldRow {
                        visible: root.has && root.e.website !== ""
                        label: "Website"; field: "website"; link: true; last: true
                        value: root.has ? root.e.website : ""
                    }
                }
            }

            Card {
                id: codeCard
                objectName: "codeCard"
                visible: root.has && root.e.hasTotp && !root.e.deleted
                height: 84
                property var info: ({})
                readonly property string code: info.code || ""
                Timer {
                    interval: 1000; repeat: true; triggeredOnStart: true
                    running: codeCard.visible
                    onTriggered: codeCard.info = backend.currentCode()
                }
                Rectangle {
                    anchors.fill: parent; anchors.margins: 4; radius: 14
                    color: codeArea.containsMouse ? Qt.rgba(1, 1, 1, 0.07) : "transparent"
                    Behavior on color { ColorAnimation { duration: 160 } }
                }
                Text { x: 20; y: 14; text: "Verification code"; color: Theme.secondary; font.pixelSize: 13 }
                Text {
                    id: codeText
                    x: 20; y: 34
                    text: codeCard.code ? codeCard.code.slice(0, 3) + " " + codeCard.code.slice(3) : (codeCard.info.error || "")
                    color: codeCard.code ? Theme.text : Theme.danger
                    font.family: codeCard.code ? Theme.mono : Qt.application.font.family
                    font.pixelSize: codeCard.code ? 28 : 15
                    font.weight: Font.Bold
                    font.letterSpacing: 2
                    onTextChanged: if (!Theme.reduceMotion) flip.restart()
                    SequentialAnimation {
                        id: flip
                        NumberAnimation { target: codeText; property: "opacity"; from: 0.2; to: 1; duration: 380; easing.type: Easing.OutCubic }
                    }
                }
                Text {
                    anchors.right: ring.left; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                    text: "Copy"
                    color: Theme.accent
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    opacity: codeArea.containsMouse ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                }
                CountdownRing {
                    id: ring
                    anchors.right: parent.right; anchors.rightMargin: 20; anchors.verticalCenter: parent.verticalCenter
                    size: 38
                    visible: codeCard.code !== ""
                    remaining: codeCard.info.remaining || 0
                    period: codeCard.info.period || 30
                }
                MouseArea {
                    id: codeArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: backend.copyField("totp")
                }
            }

            Card {
                visible: root.has && root.e.decryptable && !root.e.deleted && root.e.kind === "login"
                height: 64
                Text { x: 20; y: 12; text: "Password strength"; color: Theme.secondary; font.pixelSize: 13 }
                StrengthMeter {
                    x: 20; y: 32
                    width: parent.width - 40
                    score: root.has ? root.e.strength : -1
                }
            }

            Column {
                visible: root.has && root.e.notes !== ""
                width: parent.width
                spacing: 8
                Text { x: 4; text: "NOTES"; color: Theme.tertiary; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1.2 }
                Card {
                    height: notesText.implicitHeight + 32
                    Text {
                        id: notesText
                        x: 20; y: 16
                        width: parent.width - 40
                        text: root.has ? root.e.notes : ""
                        color: Theme.text
                        font.pixelSize: 15
                        wrapMode: Text.Wrap
                        lineHeight: 1.2
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: backend.copyField("notes")
                    }
                }
            }

            Column {
                id: history
                visible: root.has && root.e.history !== undefined && root.e.history.length > 0
                width: parent.width
                spacing: 8
                property bool expanded: false
                readonly property var items: root.has && root.e.history ? root.e.history : []
                Row {
                    x: 4
                    spacing: 8
                    Text { text: "PASSWORD HISTORY"; color: Theme.tertiary; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1.2 }
                    Text { text: history.items.length; color: Theme.tertiary; font.pixelSize: 11 }
                }
                Card {
                    height: historyColumn.height
                    Column {
                        id: historyColumn
                        width: parent.width
                        Repeater {
                            model: history.expanded ? history.items : history.items.slice(0, 3)
                            delegate: Item {
                                width: historyColumn.width
                                height: 48
                                Rectangle {
                                    anchors.fill: parent; anchors.margins: 4; radius: 12
                                    color: hArea.containsMouse ? Qt.rgba(1, 1, 1, 0.07) : "transparent"
                                }
                                Text {
                                    x: 20; anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 260
                                    text: "\u2022".repeat(12)  // earlier passwords are never shown either
                                    color: Theme.text
                                    font.pixelSize: 14
                                    font.letterSpacing: 1.5
                                    elide: Text.ElideRight
                                }
                                Text {
                                    anchors.right: parent.right; anchors.rightMargin: 20; anchors.verticalCenter: parent.verticalCenter
                                    text: hArea.containsMouse ? "Copy" : "Replaced " + modelData.changed
                                    color: hArea.containsMouse ? Theme.accent : Theme.tertiary
                                    font.pixelSize: 12
                                }
                                MouseArea {
                                    id: hArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: backend.copyHistory(index)
                                }
                            }
                        }
                    }
                }
                LinkText {
                    x: 4
                    visible: history.items.length > 3
                    text: history.expanded ? "Show fewer" : "Show all " + history.items.length
                    font.pixelSize: 13
                    onClicked: history.expanded = !history.expanded
                }
            }

            Notice {
                visible: root.has && root.e.pwned > 0
                iconName: "leak"
                tint: Theme.danger
                title: "Leaked password"
                message: root.has ? "This password has appeared " + Number(root.e.pwned).toLocaleString(Qt.locale(), "f", 0)
                         + " time" + (root.e.pwned === 1 ? "" : "s") + " in data leaks, according to Have I Been Pwned. "
                         + "Change it on the website, then here." : ""
            }
            Notice {
                visible: root.has && root.e.old
                iconName: "clock"
                tint: Theme.accent3
                title: "Old password"
                message: root.has ? "Last changed " + root.e.ageDays + " days ago. Changing passwords now and then "
                         + "limits the damage of leaks nobody noticed." : ""
            }
            Notice {
                visible: root.has && root.e.weak
                iconName: "warning"
                title: "Weak password"
                message: "It's easy to guess. Change it on the website, then edit this entry; the generator can make a strong one."
            }
            Notice {
                visible: root.has && root.e.reusedWith !== undefined && root.e.reusedWith.length > 0
                iconName: "reused"
                title: "Reused password"
                message: root.has && root.e.reusedWith ? "The same password is used for " + root.e.reusedWith.slice(0, 4).join(", ")
                         + (root.e.reusedWith.length > 4 ? ", …" : "") + ". If one of these sites is breached, the others are at risk." : ""
            }

            Text {
                x: 4
                text: root.has ? "Created " + root.e.created + "  ·  Modified " + root.e.modified : ""
                color: Theme.tertiary
                font.pixelSize: 12
            }
        }
    }

    Connections {
        target: backend
        function onSelectedChanged() { if (!Theme.reduceMotion) swap.restart() }
    }
    ParallelAnimation {
        id: swap
        NumberAnimation { target: content; property: "opacity"; from: 0.0; to: 1; duration: 260 }
        NumberAnimation { target: enterShift; property: "y"; from: 16; to: 0; duration: 420; easing.type: Easing.OutCubic }
    }
}
