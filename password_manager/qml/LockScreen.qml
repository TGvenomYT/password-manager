import QtQuick
import QtQuick.Layouts
import "."

// Everything shown while the vault is locked: GPG passphrase, unlock, create, reset.
Item {
    id: root
    property string mode: "unlock"   // gpg | unlock | create | recover | noRecovery
    readonly property bool locked: backend.lockoutSeconds > 0
    readonly property bool needsTwo: mode === "create" || mode === "recover"
    readonly property var info: copy[mode] || copy["unlock"]
    readonly property var copy: ({
        "gpg": ["Unlock the database", "Enter your GPG passphrase to connect to your password database.", "Unlock"],
        "unlock": ["Welcome back", "Enter your master password to unlock your vault.", "Unlock"],
        "create": ["Create your vault", "Choose a master password. It encrypts everything you save.", "Create Vault"],
        "recover": ["Reset master password", "Enter the recovery key you saved, then choose a new master password.", "Reset Password"],
        "noRecovery": ["No recovery key", "This vault has no recovery key, so a forgotten master password can't be reset. If you remember it, unlock the vault and the app will help you save one.", "Back"]
    })

    function fmt(seconds) {
        var m = Math.floor(seconds / 60), s = seconds % 60
        return m > 0 ? m + ":" + (s < 10 ? "0" : "") + s : s + " s"
    }
    function submit() {
        if (backend.busy || locked) return
        if (mode === "gpg") backend.submitGpg(first.text)
        else if (mode === "unlock") backend.unlock(first.text)
        else if (mode === "create") backend.createVault(first.text, second.text)
        else if (mode === "recover") backend.recover(keyField.text, first.text, second.text)
        else backend.backToUnlock()
    }
    function reset() {
        keyField.text = ""; first.text = ""; second.text = ""
        first.revealed = false; second.revealed = false
        intro.restart()
        Qt.callLater(function () { (mode === "recover" ? keyField : first).forceActiveFocus() })
    }
    onModeChanged: if (copy[mode]) reset()
    Component.onCompleted: reset()

    GlassPanel {
        id: card
        anchors.centerIn: parent
        width: 440
        height: column.implicitHeight + 76
        radius: 32
        tint: Qt.rgba(1, 1, 1, 0.075)
        transform: Translate { id: shakeShift }

        ColumnLayout {
            id: column
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 38 }
            spacing: 14

            LiquidLock {
                Layout.alignment: Qt.AlignHCenter
                Layout.bottomMargin: 6
                size: 92
                working: backend.busy
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: root.info[0]
                color: Theme.text
                font.pixelSize: 27
                font.weight: Font.Bold
            }
            Text {
                Layout.fillWidth: true
                Layout.bottomMargin: 8
                text: root.info[1]
                color: Theme.secondary
                font.pixelSize: 15
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                lineHeight: 1.15
            }
            GlassField {
                id: keyField
                visible: root.mode === "recover"
                Layout.fillWidth: true
                iconName: "key"
                mono: true
                placeholderText: "Recovery key"
                enabled: !root.locked
                onAccepted: first.forceActiveFocus()
            }
            GlassField {
                id: first
                visible: root.mode !== "noRecovery"
                Layout.fillWidth: true
                secret: true
                iconName: root.mode === "gpg" ? "key" : "lock"
                placeholderText: ({ "gpg": "GPG passphrase", "unlock": "Master password", "create": "Master password",
                                    "recover": "New master password" })[root.mode] || ""
                enabled: !root.locked
                onAccepted: root.needsTwo ? second.forceActiveFocus() : root.submit()
            }
            StrengthMeter {
                visible: root.needsTwo && first.text.length > 0
                Layout.fillWidth: true
                score: backend.strength(first.text)
            }
            Text {
                visible: root.needsTwo && first.text.length === 0
                text: "At least " + backend.minPasswordLength + " characters."
                color: Theme.tertiary
                font.pixelSize: 13
            }
            GlassField {
                id: second
                visible: root.needsTwo
                Layout.fillWidth: true
                secret: true
                iconName: "lock"
                placeholderText: "Confirm master password"
                enabled: !root.locked
                onAccepted: root.submit()
            }
            Text {
                Layout.fillWidth: true
                visible: text !== ""
                text: root.locked ? "Too many failed attempts. Try again in " + root.fmt(backend.lockoutSeconds) + "."
                                  : backend.error
                color: Theme.danger
                font.pixelSize: 14
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
            }
            GlassButton {
                Layout.fillWidth: true
                Layout.topMargin: 6
                implicitHeight: 46
                primary: true
                text: root.info[2]
                loading: backend.busy
                enabled: !root.locked
                onClicked: root.submit()
            }
            LinkText {
                Layout.alignment: Qt.AlignHCenter
                visible: root.mode === "unlock" || root.mode === "recover"
                text: root.mode === "unlock" ? "Forgot password?" : "Back to unlock"
                onClicked: root.mode === "unlock" ? backend.forgotPassword() : backend.backToUnlock()
            }
        }
    }

    ParallelAnimation {
        id: intro
        NumberAnimation { target: card; property: "opacity"; from: 0; to: 1; duration: 380 }
        NumberAnimation { target: card; property: "scale"; from: 0.92; to: 1; duration: 560; easing.type: Easing.OutBack }
    }
    SequentialAnimation {
        id: shake
        NumberAnimation { target: shakeShift; property: "x"; to: -16; duration: 55 }
        NumberAnimation { target: shakeShift; property: "x"; to: 13; duration: 70 }
        NumberAnimation { target: shakeShift; property: "x"; to: -9; duration: 70 }
        NumberAnimation { target: shakeShift; property: "x"; to: 5; duration: 70 }
        NumberAnimation { target: shakeShift; property: "x"; to: 0; duration: 80 }
    }
    Connections {
        target: backend
        function onShake() { shake.restart() }
    }
}
