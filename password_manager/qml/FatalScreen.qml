import QtQuick
import QtQuick.Layouts
import "."

Item {
    GlassPanel {
        anchors.centerIn: parent
        width: 520
        height: column.implicitHeight + 76
        radius: 32
        ColumnLayout {
            id: column
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 38 }
            spacing: 14
            Icon { Layout.alignment: Qt.AlignHCenter; name: "warning"; size: 48; color: Theme.danger; lineWidth: 1.6 }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Password Manager can't open"
                color: Theme.text
                font.pixelSize: 24
                font.weight: Font.Bold
            }
            TextEdit {
                Layout.fillWidth: true
                text: backend.fatal
                readOnly: true
                selectByMouse: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                font.pixelSize: 14
            }
            GlassButton { Layout.alignment: Qt.AlignHCenter; Layout.topMargin: 8; text: "Quit"; primary: true; onClicked: Qt.quit() }
        }
    }
}
