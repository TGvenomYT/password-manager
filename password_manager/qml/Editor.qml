import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

// Add or edit a password. Slides in over the details pane.
Item {
    id: root
    property var confirm: null
    property bool open: false
    property int entryId: -1
    property string kind: "login"
    property string initial: ""
    property bool generated: false
    property string genStyle: backend.generatorOptions.style || "random"
    property int genLength: backend.generatorOptions.length || 20
    property bool genDigits: backend.generatorOptions.digits !== false
    property bool genSymbols: backend.generatorOptions.symbols !== false
    property real shown: 0
    visible: shown > 0.001

    component FormLabel: Text {
        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
        color: Theme.secondary
        font.pixelSize: 14
    }
    enabled: open

    function values() {
        return [kind, title.text, website.text, username.text, password.text, totpField.text, notes.text].join("\u0001")
    }
    function openFor(entry, newKind) {
        var editing = entry && entry.id !== undefined
        entryId = editing ? entry.id : -1
        kind = editing ? (entry.kind || "login") : (newKind || "login")
        totpField.text = editing ? (entry.totp || "") : ""
        title.text = editing ? entry.title : ""
        website.text = editing ? entry.website : ""
        username.text = editing ? entry.username : ""
        password.text = editing ? backend.passwordFor(entry.id) : ""
        notes.text = editing ? entry.notes : ""
        password.revealed = false
        generated = false
        error.text = ""
        initial = values()
        open = true
        slideIn.restart()
        Qt.callLater(function () { (editing && kind === "login" ? password : title).forceActiveFocus() })
    }
    function close(force) {
        if (!force && values() !== initial) {
            confirm.ask("Discard changes?", "You have unsaved changes to this password.", "Discard",
                        function () { root.close(true) })
            return
        }
        open = false
        slideOut.restart()
    }
    function save() {
        error.text = ""
        backend.saveEntry(entryId, kind, title.text, website.text, username.text, password.text, totpField.text, notes.text)
    }
    function generate() {
        password.text = backend.generatePassword(genStyle, genLength, genDigits, genSymbols)
        generated = true  // stays hidden: copy it with the button in the field
    }
    function regenerate() { if (generated) generate() }

    Connections {
        target: backend
        function onEntrySaved(entryId) { if (root.open) { root.open = false; slideOut.restart() } }
        function onEditorError(message) { error.text = message; if (!Theme.reduceMotion) nudge.restart() }
    }
    NumberAnimation { id: slideIn; target: root; property: "shown"; to: 1; duration: Theme.reduceMotion ? 1 : 460; easing.type: Easing.OutCubic }
    NumberAnimation { id: slideOut; target: root; property: "shown"; to: 0; duration: Theme.reduceMotion ? 1 : 300; easing.type: Easing.InCubic }
    Shortcut { sequences: [StandardKey.Save]; enabled: root.open; onActivated: root.save() }
    Shortcut { sequence: "Escape"; enabled: root.open; onActivated: root.close(false) }

    GlassPanel {
        id: sheet
        anchors.fill: parent
        tint: Qt.rgba(0.10, 0.09, 0.17, 0.86)
        opacity: root.shown
        transform: Translate { id: sheetShift; x: (1 - root.shown) * 60 }

        RowLayout {
            id: header
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 26 }
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: (root.entryId < 0 ? "New " : "Edit ") + (root.kind === "note" ? "Secure Note" : "Password")
                color: Theme.text
                font.pixelSize: 24
                font.weight: Font.Bold
            }
            GlassButton { text: "Cancel"; onClicked: root.close(false) }
            GlassButton { text: "Save"; primary: true; iconName: "check"; loading: backend.busy; onClicked: root.save() }
        }

        Flickable {
            id: flick
            anchors { left: parent.left; right: parent.right; top: header.bottom; bottom: parent.bottom; margins: 26; topMargin: 18 }
            contentHeight: form.implicitHeight + 10
            clip: true
            boundsBehavior: Flickable.DragOverBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; visible: flick.contentHeight > flick.height }

            GridLayout {
                id: form
                width: Math.min(flick.width, 640)
                columns: 2
                columnSpacing: 16
                rowSpacing: 12
                transform: Translate { id: nudgeShift }

                FormLabel { text: "Type" }
                Segmented {
                    Layout.preferredWidth: 240
                    options: [{ value: "login", label: "Login" }, { value: "note", label: "Secure Note" }]
                    value: root.kind
                    onPicked: function (v) { root.kind = v }
                }
                FormLabel { text: "Title" }
                GlassField { id: title; objectName: "titleField"; Layout.fillWidth: true; placeholderText: "Name, like GitHub"; onAccepted: root.save() }
                FormLabel { text: "Website"; visible: root.kind === "login" }
                GlassField {
                    visible: root.kind === "login"; id: website; objectName: "websiteField"; Layout.fillWidth: true; placeholderText: "example.com"; onAccepted: root.save() }
                FormLabel { text: "User Name"; visible: root.kind === "login" }
                GlassField {
                    visible: root.kind === "login"; id: username; objectName: "usernameField"; Layout.fillWidth: true; placeholderText: "Email or user name"; onAccepted: root.save() }
                FormLabel { text: "Password"; visible: root.kind === "login" }
                GlassField {
                    id: password
                    visible: root.kind === "login"
                    objectName: "passwordField"
                    Layout.fillWidth: true
                    secret: true
                    revealable: false  // passwords are never shown, only copied
                    placeholderText: "Password"
                    onTextEdited: root.generated = false
                    onAccepted: root.save()
                    IconButton {
                        objectName: "copyPasswordButton"
                        visible: password.text !== ""
                        iconName: "copy"
                        size: 32
                        anchors.right: parent.right
                        anchors.rightMargin: 7
                        anchors.verticalCenter: parent.verticalCenter
                        tip: "Copy"
                        onClicked: backend.copyPassword(password.text)
                    }
                }
                Item { width: 1; height: 1; visible: root.kind === "login" }
                StrengthMeter { Layout.fillWidth: true; visible: root.kind === "login"; score: backend.strength(password.text) }

                Item { width: 1; height: 1; visible: root.kind === "login" }
                Rectangle {
                    visible: root.kind === "login"
                    Layout.fillWidth: true
                    implicitHeight: gen.implicitHeight + 32
                    radius: 16
                    color: Theme.glassInner
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, 0.08)
                    ColumnLayout {
                        id: gen
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                        spacing: 12
                        RowLayout {
                            spacing: 12
                            GlassButton {
                                text: "Generate"
                                primary: true
                                iconName: "sparkle"
                                onClicked: root.generate()
                            }
                            Segmented {
                                Layout.preferredWidth: 220
                                options: [{ value: "random", label: "Random" }, { value: "memorable", label: "Memorable" }]
                                value: root.genStyle
                                onPicked: function (v) { root.genStyle = v; root.regenerate() }
                            }
                        }
                        RowLayout {
                            visible: root.genStyle === "random"
                            spacing: 12
                            Text { text: "Length"; color: Theme.secondary; font.pixelSize: 13 }
                            LiquidSlider {
                                Layout.preferredWidth: 180
                                from: 8; to: 64; stepSize: 1
                                value: root.genLength
                                onMoved: { root.genLength = Math.round(value); root.regenerate() }
                            }
                            Text {
                                text: root.genLength
                                color: Theme.text
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                Layout.preferredWidth: 26
                            }
                        }
                        RowLayout {
                            visible: root.genStyle === "random"
                            spacing: 20
                            LiquidSwitch {
                                text: "Numbers"
                                checked: root.genDigits
                                onToggled: { root.genDigits = checked; root.regenerate() }
                            }
                            LiquidSwitch {
                                text: "Symbols"
                                checked: root.genSymbols
                                onToggled: { root.genSymbols = checked; root.regenerate() }
                            }
                        }
                        Text {
                            visible: root.genStyle === "memorable"
                            text: "Three easy-to-type groups, like kabomi-Tefuna-ri7oke."
                            color: Theme.tertiary
                            font.pixelSize: 13
                        }
                    }
                }

                FormLabel { text: "2FA Key"; visible: root.kind === "login" }
                Column {
                    visible: root.kind === "login"
                    Layout.fillWidth: true
                    spacing: 6
                    readonly property var preview: backend.totpPreview(totpField.text)
                    GlassField {
                        id: totpField
                        width: parent.width
                        iconName: "timer"
                        mono: true
                        placeholderText: "Secret key or otpauth:// link (optional)"
                        onAccepted: root.save()
                    }
                    Text {
                        width: parent.width
                        visible: text !== ""
                        text: parent.preview.valid ? "Current code: " + parent.preview.code.slice(0, 3) + " " + parent.preview.code.slice(3)
                              : parent.preview.error
                        color: parent.preview.valid ? Theme.success : Theme.danger
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                    }
                }

                FormLabel { text: "Notes"; Layout.alignment: Qt.AlignRight | Qt.AlignTop; Layout.topMargin: 12 }
                TextArea {
                    id: notes
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.kind === "note" ? 260 : 120
                    wrapMode: TextEdit.Wrap
                    color: Theme.text
                    placeholderText: "Anything else: security questions, PINs, recovery codes…"
                    placeholderTextColor: Theme.tertiary
                    selectionColor: Theme.tint(Theme.accent, 0.5)
                    font.pixelSize: 15
                    padding: 14
                    background: Rectangle {
                        radius: 13
                        color: Qt.rgba(1, 1, 1, notes.activeFocus ? 0.11 : 0.06)
                        border.width: 1
                        border.color: notes.activeFocus ? Theme.accent : Theme.glassBorder
                    }
                }
                Item { width: 1; height: 1 }
                Text {
                    Layout.fillWidth: true
                    text: "Notes are encrypted like everything else."
                    color: Theme.tertiary
                    font.pixelSize: 12
                }
                Item { width: 1; height: 1 }
                Text {
                    id: error
                    Layout.fillWidth: true
                    visible: text !== ""
                    color: Theme.danger
                    font.pixelSize: 14
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    SequentialAnimation {
        id: nudge
        NumberAnimation { target: nudgeShift; property: "x"; to: -10; duration: 60 }
        NumberAnimation { target: nudgeShift; property: "x"; to: 8; duration: 70 }
        NumberAnimation { target: nudgeShift; property: "x"; to: 0; duration: 90 }
    }
}
