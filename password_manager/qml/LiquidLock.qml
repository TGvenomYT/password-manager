import QtQuick
import QtQuick.Effects
import "."

// The app icon itself (packaging/icon.svg, made by packaging/make_icons.py), so every screen shows the
// same lock as the Dock, taskbar and Start menu. It is drawn from three layers that stack into exactly
// assets/app-icon.png; the middle one, the shackle, lifts while the vault is unlocking.
// `size` is the width of the rounded tile. The icon's soft shadow spills a little outside it.
Item {
    id: root
    property real size: 96
    property bool working: false
    property bool animate: !Theme.reduceMotion
    property bool glow: true
    width: size
    height: size

    // The SVG is 1024 wide with the tile from 100 to 924, as macOS expects.
    readonly property real canvas: size * 1024 / 824
    readonly property real inset: size * 100 / 824
    readonly property int pixels: Math.min(512, Math.ceil(canvas * Screen.devicePixelRatio))

    Rectangle {
        id: halo
        anchors.centerIn: parent
        width: root.size * 0.9; height: width; radius: width / 2
        color: Theme.accent
        visible: false
    }
    MultiEffect {
        visible: root.glow
        anchors.fill: halo
        source: halo
        blurEnabled: true; blur: 1.0; blurMax: 48
        autoPaddingEnabled: true
        opacity: 0.5
        SequentialAnimation on opacity {
            running: root.animate && root.glow; loops: Animation.Infinite
            NumberAnimation { to: 0.8; duration: 1800; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.4; duration: 1800; easing.type: Easing.InOutSine }
        }
    }

    Item {
        id: art
        x: -root.inset
        y: -root.inset
        width: root.canvas
        height: root.canvas

        component Layer: Image {
            width: art.width
            height: art.height
            sourceSize: Qt.size(root.pixels, root.pixels)  // decoded at the size it's shown: sharp, not blurry
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
        }
        Layer { source: "../assets/icon/back.png" }
        Layer {
            id: shackle
            source: "../assets/icon/shackle.png"
            property real lift: root.working ? -root.size * 0.07 : 0
            Behavior on lift { enabled: root.animate; SpringAnimation { spring: 3; damping: 0.25 } }
            transform: Translate { y: shackle.lift }
        }
        Layer { source: "../assets/icon/front.png" }
    }
}
