import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Shapes
import "."

// The Security overview: a score, a tile per kind of problem, and the leak check.
GlassPanel {
    id: root
    readonly property var sec: backend.security
    property real shownScore: 0
    readonly property color scoreColor: sec.score >= 85 ? Theme.success : sec.score >= 60 ? Theme.warning : Theme.danger
    readonly property string verdict: sec.logins === 0 ? "Nothing to check yet"
                                      : sec.score >= 85 ? "Excellent" : sec.score >= 60 ? "Could be better" : "Needs attention"

    function animateScore() {
        scoreIn.from = shownScore
        scoreIn.to = sec.score
        scoreIn.restart()
    }
    Component.onCompleted: animateScore()
    Connections { target: backend; function onSecurityChanged() { root.animateScore() } }
    NumberAnimation { id: scoreIn; target: root; property: "shownScore"; duration: Theme.reduceMotion ? 1 : 1500; easing.type: Easing.OutCubic }

    component Tile: Rectangle {
        id: tile
        property string iconName: ""
        property color tone: Theme.accent
        property int count: 0
        property string label: ""
        property string detail: ""
        property string view: ""
        Layout.fillWidth: true
        implicitHeight: 128
        radius: 20
        color: Theme.glassInner
        border.width: 1
        border.color: area.containsMouse ? Theme.tint(tone, 0.55) : Qt.rgba(1, 1, 1, 0.08)
        scale: area.pressed ? 0.97 : (area.containsMouse ? 1.025 : 1)
        Behavior on scale { enabled: !Theme.reduceMotion; SpringAnimation { spring: 4; damping: 0.3 } }
        Behavior on border.color { ColorAnimation { duration: 180 } }
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.tint(tile.tone, area.containsMouse ? 0.20 : 0.11) }
            GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0.03) }
        }
        Rectangle {
            x: 18; y: 18
            width: 38; height: 38; radius: 12
            color: Theme.tint(tile.tone, 0.22)
            Icon { anchors.centerIn: parent; name: tile.iconName; size: 20; color: tile.tone }
        }
        Text {
            anchors.right: parent.right; anchors.rightMargin: 20; y: 14
            text: tile.count
            color: tile.count > 0 && tile.view !== "codes" && tile.view !== "all" ? tile.tone : Theme.text
            font.pixelSize: 34
            font.weight: Font.Bold
        }
        Text { x: 18; y: 70; text: tile.label; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
        Text {
            x: 18; y: 92
            width: tile.width - 36
            text: tile.detail
            color: Theme.tertiary
            font.pixelSize: 12
            elide: Text.ElideRight
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: backend.setView(tile.view)
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: 32
        contentHeight: column.height + 10
        clip: true
        boundsBehavior: Flickable.DragOverBounds

        Column {
            id: column
            width: parent.width
            spacing: 26

            Column {
                spacing: 4
                Text { text: "Security"; color: Theme.text; font.pixelSize: 30; font.weight: Font.Bold }
                Text { text: "How safe your saved passwords are, checked on this computer."; color: Theme.secondary; font.pixelSize: 15 }
            }

            RowLayout {
                width: parent.width
                spacing: 32

                Item {
                    implicitWidth: 210; implicitHeight: 210
                    Rectangle {
                        id: halo
                        anchors.centerIn: parent
                        width: 170; height: 170; radius: 85
                        color: root.scoreColor
                        visible: false
                    }
                    MultiEffect {
                        anchors.fill: halo
                        source: halo
                        blurEnabled: true; blur: 1.0; blurMax: 64
                        autoPaddingEnabled: true
                        opacity: 0.35
                        SequentialAnimation on opacity {
                            running: !Theme.reduceMotion; loops: Animation.Infinite
                            NumberAnimation { to: 0.55; duration: 2200; easing.type: Easing.InOutSine }
                            NumberAnimation { to: 0.3; duration: 2200; easing.type: Easing.InOutSine }
                        }
                    }
                    Shape {
                        anchors.fill: parent
                        preferredRendererType: Shape.CurveRenderer
                        ShapePath {
                            strokeColor: Qt.rgba(1, 1, 1, 0.10); strokeWidth: 16; fillColor: "transparent"
                            PathAngleArc { centerX: 105; centerY: 105; radiusX: 92; radiusY: 92; startAngle: 0; sweepAngle: 360 }
                        }
                        ShapePath {
                            strokeColor: root.scoreColor; strokeWidth: 16; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                            PathAngleArc { centerX: 105; centerY: 105; radiusX: 92; radiusY: 92; startAngle: -90
                                           sweepAngle: 360 * Math.max(0.001, root.shownScore) / 100 }
                        }
                    }
                    Column {
                        anchors.centerIn: parent
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: Math.round(root.shownScore)
                            color: Theme.text
                            font.pixelSize: 58
                            font.weight: Font.Bold
                        }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "out of 100"; color: Theme.tertiary; font.pixelSize: 13 }
                    }
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 12
                    Text { text: root.verdict; color: root.scoreColor; font.pixelSize: 26; font.weight: Font.Bold }
                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        color: Theme.secondary
                        font.pixelSize: 14
                        lineHeight: 1.2
                        text: root.sec.logins === 0 ? "Add some passwords and they'll be checked here."
                              : root.sec.logins + " logins checked. Weak and leaked passwords cost the most, then reused, "
                                + "then ones you haven't changed in over a year."
                    }
                    Rectangle {
                        width: parent.width
                        implicitHeight: leakColumn.height + 32
                        radius: 18
                        color: Theme.glassInner
                        border.width: 1
                        border.color: Qt.rgba(1, 1, 1, 0.08)
                        Column {
                            id: leakColumn
                            x: 18; y: 16
                            width: parent.width - 36
                            spacing: 10
                            RowLayout {
                                width: parent.width
                                spacing: 12
                                Icon { name: "leak"; size: 22; color: Theme.danger }
                                Column {
                                    Layout.fillWidth: true
                                    Text { text: "Leak check"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                                    Text {
                                        width: parent.width
                                        text: root.sec.checked ? "Last checked " + root.sec.checkedAt : "Not checked yet this session"
                                        color: Theme.tertiary
                                        font.pixelSize: 12
                                    }
                                }
                                GlassButton {
                                    objectName: "checkLeaks"
                                    text: backend.checking ? "Checking…" : "Check Now"
                                    primary: true
                                    loading: backend.checking
                                    enabled: !backend.checking && root.sec.logins > 0
                                    onClicked: backend.checkLeaks()
                                }
                            }
                            Rectangle {  // a shimmer while the check runs
                                visible: backend.checking
                                width: parent.width; height: 4; radius: 2
                                color: Qt.rgba(1, 1, 1, 0.08)
                                clip: true
                                Rectangle {
                                    width: parent.width * 0.35; height: parent.height; radius: 2
                                    gradient: Gradient {
                                        orientation: Gradient.Horizontal
                                        GradientStop { position: 0.0; color: Theme.tint(Theme.accent, 0) }
                                        GradientStop { position: 0.5; color: Theme.accent2 }
                                        GradientStop { position: 1.0; color: Theme.tint(Theme.accent, 0) }
                                    }
                                    NumberAnimation on x {
                                        running: backend.checking; loops: Animation.Infinite
                                        from: -width; to: leakColumn.width; duration: 1100; easing.type: Easing.InOutQuad
                                    }
                                }
                            }
                            Text {
                                width: parent.width
                                wrapMode: Text.Wrap
                                color: Theme.tertiary
                                font.pixelSize: 12
                                text: "Compares your passwords with Have I Been Pwned's list of leaked passwords. Only the first "
                                      + "5 characters of each password's SHA-1 hash leave this computer, never the password."
                            }
                        }
                    }
                }
            }

            GridLayout {
                width: parent.width
                columns: width > 760 ? 3 : 2
                columnSpacing: 14
                rowSpacing: 14
                Tile { iconName: "leak"; tone: Theme.danger; view: "pwned"; count: root.sec.pwned; label: "Leaked"
                       detail: root.sec.checked ? "Found in known data leaks" : "Run a leak check to find out" }
                Tile { iconName: "warning"; tone: Theme.warning; view: "weak"; count: root.sec.weak; label: "Weak"
                       detail: "Easy to guess" }
                Tile { iconName: "reused"; tone: Theme.warning; view: "reused"; count: root.sec.reused; label: "Reused"
                       detail: "Same password on several sites" }
                Tile { iconName: "clock"; tone: Theme.accent3; view: "old"; count: root.sec.old; label: "Old"
                       detail: "Unchanged for over a year" }
                Tile { iconName: "timer"; tone: Theme.success; view: "codes"; count: root.sec.codes; label: "Two-factor codes"
                       detail: root.sec.logins ? root.sec.codes + " of " + root.sec.logins + " logins have 2FA" : "None yet" }
                Tile { iconName: "shield"; tone: Theme.accent; view: "all"; count: root.sec.logins; label: "Logins checked"
                       detail: "Open all items" }
            }
        }
    }
}
