import QtQuick
import QtQuick.Shapes

// One organic shape whose four "radii" breathe at different speeds, so it never repeats exactly.
Item {
    id: blob
    property color color: "#8B7BFF"
    property real radius: 200
    property bool running: true
    property int period: 9000
    property real a1: 1
    property real a2: 1
    property real a3: 1
    property real a4: 1
    readonly property real cx: width / 2
    readonly property real cy: height / 2
    readonly property real k: 0.5523
    width: radius * 3
    height: radius * 3

    Shape {
        anchors.fill: parent
        ShapePath {
            fillColor: blob.color
            strokeColor: "transparent"
            startX: blob.cx + blob.radius * blob.a1
            startY: blob.cy
            PathCubic {
                x: blob.cx; y: blob.cy + blob.radius * blob.a2
                control1X: blob.cx + blob.radius * blob.a1; control1Y: blob.cy + blob.k * blob.radius * blob.a1
                control2X: blob.cx + blob.k * blob.radius * blob.a2; control2Y: blob.cy + blob.radius * blob.a2
            }
            PathCubic {
                x: blob.cx - blob.radius * blob.a3; y: blob.cy
                control1X: blob.cx - blob.k * blob.radius * blob.a2; control1Y: blob.cy + blob.radius * blob.a2
                control2X: blob.cx - blob.radius * blob.a3; control2Y: blob.cy + blob.k * blob.radius * blob.a3
            }
            PathCubic {
                x: blob.cx; y: blob.cy - blob.radius * blob.a4
                control1X: blob.cx - blob.radius * blob.a3; control1Y: blob.cy - blob.k * blob.radius * blob.a3
                control2X: blob.cx - blob.k * blob.radius * blob.a4; control2Y: blob.cy - blob.radius * blob.a4
            }
            PathCubic {
                x: blob.cx + blob.radius * blob.a1; y: blob.cy
                control1X: blob.cx + blob.k * blob.radius * blob.a4; control1Y: blob.cy - blob.radius * blob.a4
                control2X: blob.cx + blob.radius * blob.a1; control2Y: blob.cy - blob.k * blob.radius * blob.a1
            }
        }
    }

    SequentialAnimation on a1 {
        running: blob.running; loops: Animation.Infinite
        NumberAnimation { to: 1.28; duration: blob.period * 0.52; easing.type: Easing.InOutSine }
        NumberAnimation { to: 0.82; duration: blob.period * 0.48; easing.type: Easing.InOutSine }
    }
    SequentialAnimation on a2 {
        running: blob.running; loops: Animation.Infinite
        NumberAnimation { to: 0.80; duration: blob.period * 0.61; easing.type: Easing.InOutSine }
        NumberAnimation { to: 1.22; duration: blob.period * 0.57; easing.type: Easing.InOutSine }
    }
    SequentialAnimation on a3 {
        running: blob.running; loops: Animation.Infinite
        NumberAnimation { to: 1.24; duration: blob.period * 0.47; easing.type: Easing.InOutSine }
        NumberAnimation { to: 0.86; duration: blob.period * 0.66; easing.type: Easing.InOutSine }
    }
    SequentialAnimation on a4 {
        running: blob.running; loops: Animation.Infinite
        NumberAnimation { to: 0.84; duration: blob.period * 0.55; easing.type: Easing.InOutSine }
        NumberAnimation { to: 1.26; duration: blob.period * 0.43; easing.type: Easing.InOutSine }
    }
    RotationAnimation on rotation {
        running: blob.running; loops: Animation.Infinite
        from: 0; to: 360; duration: blob.period * 5
    }
}
