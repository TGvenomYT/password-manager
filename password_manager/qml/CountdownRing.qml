import QtQuick
import QtQuick.Shapes
import "."

// A ring that drains as a 2FA code's time runs out, turning amber near the end.
Item {
    id: root
    property real size: 34
    property int remaining: 30
    property int period: 30
    property real progress: period > 0 ? remaining / period : 0
    Behavior on progress { enabled: !Theme.reduceMotion; NumberAnimation { duration: 950; easing.type: Easing.Linear } }
    readonly property color tone: remaining <= 6 ? Theme.warning : Theme.accent3
    width: size
    height: size

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: Qt.rgba(1, 1, 1, 0.12)
            strokeWidth: 3.5
            fillColor: "transparent"
            PathAngleArc { centerX: root.size / 2; centerY: root.size / 2; radiusX: root.size / 2 - 3; radiusY: root.size / 2 - 3
                           startAngle: 0; sweepAngle: 360 }
        }
        ShapePath {
            strokeColor: root.tone
            strokeWidth: 3.5
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: root.size / 2; centerY: root.size / 2; radiusX: root.size / 2 - 3; radiusY: root.size / 2 - 3
                           startAngle: -90; sweepAngle: 360 * root.progress }
        }
    }
    Text {
        anchors.centerIn: parent
        text: root.remaining
        color: root.tone
        font.pixelSize: root.size * 0.34
        font.weight: Font.Bold
    }
}
