import QtQuick
import QtQuick.Shapes
import "."

// A spinning gradient arc.
Item {
    id: root
    property real size: 22
    property color color: Theme.accent
    width: size
    height: size
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: root.size * 0.12
            strokeColor: root.color
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            startX: root.size / 2; startY: root.size * 0.08
            PathArc {
                x: root.size * 0.92; y: root.size / 2
                radiusX: root.size * 0.42; radiusY: root.size * 0.42
            }
        }
    }
    RotationAnimation on rotation {
        running: root.visible; loops: Animation.Infinite
        from: 0; to: 360; duration: 800
    }
}
