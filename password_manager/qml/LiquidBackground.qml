import QtQuick
import QtQuick.Effects
import QtQuick.Shapes
import "."

// The window's backdrop: a five-colour gradient that slowly turns, with large translucent liquid
// shapes flowing over it and everything blurred together, so colour fills the whole window.
Item {
    id: root
    readonly property bool animate: !Theme.reduceMotion
    property real phase: 0
    // theme colours, eased so switching themes melts from one palette to the next
    property color k1: Theme.c1
    property color k2: Theme.c2
    property color k3: Theme.c3
    property color k4: Theme.c4
    property color k5: Theme.c5
    Behavior on k1 { ColorAnimation { duration: 1400; easing.type: Easing.InOutQuad } }
    Behavior on k2 { ColorAnimation { duration: 1400; easing.type: Easing.InOutQuad } }
    Behavior on k3 { ColorAnimation { duration: 1400; easing.type: Easing.InOutQuad } }
    Behavior on k4 { ColorAnimation { duration: 1400; easing.type: Easing.InOutQuad } }
    Behavior on k5 { ColorAnimation { duration: 1400; easing.type: Easing.InOutQuad } }

    NumberAnimation on phase {
        running: root.animate; loops: Animation.Infinite
        from: 0; to: Math.PI * 2; duration: 48000
    }

    Item {
        id: liquid
        anchors.fill: parent
        visible: false

        Shape {  // the gradient: its direction rotates once per cycle
            anchors.fill: parent
            ShapePath {
                strokeColor: "transparent"
                fillGradient: LinearGradient {
                    x1: root.width * (0.5 - 0.6 * Math.cos(root.phase)); y1: root.height * (0.5 - 0.6 * Math.sin(root.phase))
                    x2: root.width * (0.5 + 0.6 * Math.cos(root.phase)); y2: root.height * (0.5 + 0.6 * Math.sin(root.phase))
                    GradientStop { position: 0.0; color: root.k1 }
                    GradientStop { position: 0.25; color: root.k2 }
                    GradientStop { position: 0.5; color: root.k3 }
                    GradientStop { position: 0.75; color: root.k4 }
                    GradientStop { position: 1.0; color: root.k5 }
                }
                startX: 0; startY: 0
                PathLine { x: root.width; y: 0 }
                PathLine { x: root.width; y: root.height }
                PathLine { x: 0; y: root.height }
                PathLine { x: 0; y: 0 }
            }
        }
        Blob {
            color: root.k1; opacity: 0.75; radius: root.width * 0.32; period: 14000; running: root.animate
            x: root.width * (0.18 + 0.10 * Math.sin(root.phase)) - width / 2
            y: root.height * (0.22 + 0.12 * Math.cos(root.phase * 2)) - height / 2
        }
        Blob {
            color: root.k2; opacity: 0.7; radius: root.width * 0.28; period: 17000; running: root.animate
            x: root.width * (0.78 + 0.10 * Math.cos(root.phase)) - width / 2
            y: root.height * (0.18 + 0.14 * Math.sin(root.phase * 2)) - height / 2
        }
        Blob {
            color: root.k3; opacity: 0.7; radius: root.width * 0.26; period: 12000; running: root.animate
            x: root.width * (0.82 + 0.08 * Math.sin(root.phase * 3)) - width / 2
            y: root.height * (0.82 + 0.10 * Math.cos(root.phase)) - height / 2
        }
        Blob {
            color: root.k4; opacity: 0.7; radius: root.width * 0.30; period: 16000; running: root.animate
            x: root.width * (0.22 + 0.12 * Math.cos(root.phase * 2)) - width / 2
            y: root.height * (0.86 + 0.08 * Math.sin(root.phase)) - height / 2
        }
        Blob {
            color: root.k5; opacity: 0.6; radius: root.width * 0.20; period: 10000; running: root.animate
            x: root.width * (0.50 + 0.16 * Math.sin(root.phase * 2)) - width / 2
            y: root.height * (0.50 + 0.16 * Math.cos(root.phase * 3)) - height / 2
        }
    }

    MultiEffect {
        anchors.fill: parent
        source: liquid
        autoPaddingEnabled: false
        blurEnabled: true
        blur: 1.0
        blurMax: 64
        saturation: 0.05
    }

    // Deepen it so white text and glass stay readable on every colour.
    Rectangle { anchors.fill: parent; color: Qt.rgba(0.03, 0.03, 0.08, 0.40) }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0, 0, 0, 0.0) }
            GradientStop { position: 1.0; color: Qt.rgba(0.01, 0.01, 0.04, 0.35) }
        }
    }
}
