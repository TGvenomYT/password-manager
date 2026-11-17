import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs
import QtCore
import "."

ModalCard {
    id: root
    cardWidth: 580
    property var confirm: null
    property var changePassword: null
    property var backupDialog: null
    property string tab: "appearance"
    property string message: ""
    property bool messageIsError: false
    readonly property int inner: cardWidth - 56
    onOpened: message = ""
    Connections {
        target: backend
        function onDialogMessage(text, isError) {
            if (root.opened && !(root.changePassword && root.changePassword.opened)
                    && !(root.backupDialog && root.backupDialog.opened)) {
                root.message = text
                root.messageIsError = isError
            }
        }
    }

    component Section: Text {
        color: Theme.tertiary
        font.pixelSize: 11
        font.weight: Font.Bold
        font.letterSpacing: 1.2
    }
    component Setting: RowLayout {
        property alias label: label.text
        width: root.inner
        spacing: 16
        Text { id: label; Layout.fillWidth: true; color: Theme.text; font.pixelSize: 14; wrapMode: Text.Wrap }
    }

    Row {
        spacing: 12
        Icon { name: "gear"; size: 24; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
        Text { text: "Settings"; color: Theme.text; font.pixelSize: 23; font.weight: Font.Bold }
    }
    Segmented {
        width: root.inner
        options: [{ value: "appearance", label: "Appearance" }, { value: "security", label: "Security" },
                  { value: "alerts", label: "Alerts" }, { value: "data", label: "Data" }]
        value: root.tab
        onPicked: function (v) { root.tab = v; root.message = "" }
    }

    Column {
        visible: root.tab === "appearance"
        width: root.inner
        spacing: 14
        Section { text: "THEME" }
        Row {
            spacing: 18
            Repeater {
                model: Theme.themeNames
                delegate: Column {
                    spacing: 8
                    Item {
                        width: 92; height: 92
                        scale: swatchArea.containsMouse ? 1.06 : 1
                        Behavior on scale { enabled: !Theme.reduceMotion; SpringAnimation { spring: 4; damping: 0.3 } }
                        Rectangle {
                            anchors.fill: parent
                            radius: 26
                            rotation: 35
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: Theme.palettes[modelData].colors[0] }
                                GradientStop { position: 0.35; color: Theme.palettes[modelData].colors[1] }
                                GradientStop { position: 0.7; color: Theme.palettes[modelData].colors[2] }
                                GradientStop { position: 1.0; color: Theme.palettes[modelData].colors[4] }
                            }
                        }
                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: -5
                            radius: 30
                            color: "transparent"
                            border.width: 3
                            border.color: "white"
                            opacity: backend.theme === modelData ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: 200 } }
                        }
                        MouseArea {
                            id: swatchArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: backend.setTheme(modelData)
                        }
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: Theme.palettes[modelData].label
                        color: backend.theme === modelData ? Theme.text : Theme.secondary
                        font.pixelSize: 13
                        font.weight: backend.theme === modelData ? Font.DemiBold : Font.Normal
                    }
                }
            }
        }
        Item { width: 1; height: 4 }
        Setting {
            label: "Reduce motion"
            LiquidSwitch { checked: backend.reduceMotion; onToggled: backend.setReduceMotion(checked) }
        }
        Text {
            width: root.inner
            text: "Stills the liquid background and the springy movement."
            color: Theme.tertiary
            font.pixelSize: 12
        }
    }

    Column {
        visible: root.tab === "security"
        width: root.inner
        spacing: 14
        Setting {
            label: "Lock the vault"
            GlassCombo {
                choices: [{ label: "After 1 minute", value: 1 }, { label: "After 5 minutes", value: 5 },
                          { label: "After 15 minutes", value: 15 }, { label: "After 30 minutes", value: 30 },
                          { label: "After 1 hour", value: 60 }, { label: "Never", value: 0 }]
                current: backend.autoLockMinutes
                onChosen: function (value) { backend.setAutoLock(value) }
            }
        }
        Setting {
            label: "Clear copied passwords and codes"
            GlassCombo {
                choices: [{ label: "After 15 seconds", value: 15 }, { label: "After 30 seconds", value: 30 },
                          { label: "After 1 minute", value: 60 }, { label: "After 2 minutes", value: 120 },
                          { label: "Never", value: 0 }]
                current: backend.clipboardSeconds
                onChosen: function (value) { backend.setClipboardSeconds(value) }
            }
        }
        Row {
            spacing: 10
            topPadding: 4
            GlassButton { text: "Change Master Password…"; iconName: "lock"; onClicked: root.changePassword.open() }
            GlassButton { text: "New Recovery Key…"; iconName: "key"; onClicked: { root.close(); backend.newRecoveryKey() } }
        }
    }

    Column {
        id: alertsTab
        visible: root.tab === "alerts"
        width: root.inner
        spacing: 14
        readonly property bool configured: backend.alertEmail !== ""
        readonly property string helpUrl: backend.appPasswordHelp(alertAddress.text)
        property bool settingUp: false  // switched on before alerts are set up: show the setup form
        Connections {
            target: backend
            function onAlertsChanged() {
                if (backend.alertEmail !== "") {
                    alertPassword.text = ""
                    alertsTab.settingUp = false
                }
            }
        }
        Setting {
            label: "Email me about security events"
            LiquidSwitch {
                id: alertSwitch
                objectName: "alertSwitch"
                checked: backend.emailAlerts || alertsTab.settingUp
                onToggled: {
                    if (alertsTab.configured) {
                        backend.setEmailAlerts(checked)  // pause or resume
                    } else {
                        alertsTab.settingUp = checked
                        root.message = ""
                        if (checked)
                            alertAddress.forceActiveFocus()
                    }
                    checked = Qt.binding(function () { return backend.emailAlerts || alertsTab.settingUp })
                }
            }
        }
        Text {
            width: root.inner
            wrapMode: Text.Wrap
            color: Theme.tertiary
            font.pixelSize: 12
            lineHeight: 1.15
            text: "You'll get an email when someone is locked out after wrong master passwords, when the recovery "
                  + "key is used, when your master password or recovery key changes, and when a leak check finds "
                  + "leaked passwords. Alerts go from your address to itself and never contain your passwords."
        }

        Rectangle {
            visible: alertsTab.configured
            width: root.inner
            height: 62
            radius: 16
            color: Qt.rgba(1, 1, 1, 0.06)
            border.width: 1
            border.color: Theme.glassBorder
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 12
                spacing: 12
                Icon { name: "mail"; size: 20; color: Theme.accent }
                Column {
                    Layout.fillWidth: true
                    Text { text: backend.emailAlerts ? "Sending alerts to" : "Alerts are paused for"; color: Theme.tertiary; font.pixelSize: 12 }
                    Text { width: parent.width; text: backend.alertEmail; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideMiddle }
                }
                GlassButton { objectName: "testEmailButton"; text: "Send Test"; loading: backend.emailBusy; enabled: !backend.emailBusy; onClicked: { root.message = ""; backend.sendTestEmail() } }
                GlassButton {
                    text: "Remove…"
                    destructive: true
                    enabled: !backend.emailBusy
                    onClicked: root.confirm.ask("Remove email alerts?", "Alerts stop, and the app password for "
                                                + backend.alertEmail + " is deleted from this computer.", "Remove",
                                                function () { backend.removeEmailAlerts() })
                }
            }
        }

        Column {
            objectName: "alertSetupForm"
            visible: !alertsTab.configured && alertsTab.settingUp
            width: root.inner
            spacing: 12
            Section { text: "SET UP" }
            GlassField {
                id: alertAddress
                objectName: "alertAddress"
                width: root.inner
                iconName: "mail"
                placeholderText: "Your Gmail, iCloud Mail or Yahoo Mail address"
                inputMethodHints: Qt.ImhEmailCharactersOnly | Qt.ImhNoAutoUppercase
                onAccepted: alertPassword.forceActiveFocus()
            }
            GlassField {
                id: alertPassword
                objectName: "alertPassword"
                width: root.inner
                secret: true
                mono: revealed
                iconName: "key"
                placeholderText: "App password for that account"
                onAccepted: if (setupButton.enabled) setupButton.clicked()
            }
            Text {
                width: root.inner
                wrapMode: Text.Wrap
                color: Theme.tertiary
                font.pixelSize: 12
                text: "An app password is a separate password your email account makes for apps like this one. "
                      + "Your normal email password won't work. It's kept in this computer's password store."
            }
            RowLayout {
                width: root.inner
                LinkText {
                    visible: alertsTab.helpUrl !== ""
                    text: "Make an app password"
                    font.pixelSize: 13
                    onClicked: backend.openWebsite(alertsTab.helpUrl)
                }
                Item { Layout.fillWidth: true }
                GlassButton {
                    id: setupButton
                    objectName: "setupAlertsButton"
                    text: "Send Test Email & Turn On"
                    iconName: "mail"
                    primary: true
                    loading: backend.emailBusy
                    enabled: !backend.emailBusy && alertAddress.text.trim() !== "" && alertPassword.text !== ""
                    onClicked: { root.message = ""; backend.setupEmailAlerts(alertAddress.text, alertPassword.text) }
                }
            }
        }
    }

    Column {
        visible: root.tab === "data"
        width: root.inner
        spacing: 14
        Section { text: "ENCRYPTED BACKUP" }
        Setting {
            label: "A single file with everything, sealed with a backup password. Safe to keep on a USB stick or in cloud storage."
            Row {
                spacing: 8
                GlassButton { text: "Back Up…"; iconName: "archive"; onClicked: root.backupDialog.openFor("export") }
                GlassButton { text: "Restore…"; iconName: "import"; onClicked: root.backupDialog.openFor("import") }
            }
        }
        Rectangle { width: root.inner; height: 1; color: Qt.rgba(1, 1, 1, 0.08) }
        Section { text: "CSV" }
        Setting {
            label: "Bring in passwords exported from Chrome, Safari, Firefox, Edge, Bitwarden or 1Password, including 2FA keys."
            GlassButton { text: "Import…"; iconName: "import"; onClicked: root.importDialog.open() }
        }
        Setting {
            label: "Save every password to a CSV file. The file isn't encrypted, so delete it when you're done."
            GlassButton {
                text: "Export…"
                iconName: "export"
                onClicked: root.confirm.ask("Export passwords?", "The CSV file will contain every password as plain, "
                                            + "readable text. Anyone who can open the file can read them.", "Export",
                                            function () { root.exportDialog.open() })
            }
        }
    }

    Text {
        width: root.inner
        visible: root.message !== ""
        text: root.message
        color: root.messageIsError ? Theme.danger : Theme.success
        font.pixelSize: 13
        wrapMode: Text.Wrap
    }
    Row {
        anchors.right: parent.right
        GlassButton { text: "Done"; primary: true; onClicked: root.close() }
    }

    property FileDialog importDialog: FileDialog {
        title: "Import Passwords"
        fileMode: FileDialog.OpenFile
        nameFilters: ["CSV files (*.csv)", "All files (*)"]
        onAccepted: backend.importCsv(selectedFile.toString())
    }
    property FileDialog exportDialog: FileDialog {
        title: "Export Passwords"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "csv"
        nameFilters: ["CSV files (*.csv)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        selectedFile: currentFolder + "/Passwords.csv"
        onAccepted: backend.exportCsv(selectedFile.toString())
    }
}
