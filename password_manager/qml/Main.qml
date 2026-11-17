import QtQuick
import QtQuick.Controls.Basic
import "."

ApplicationWindow {
    id: win
    width: 1220
    height: 780
    minimumWidth: 1020
    minimumHeight: 660
    visible: true
    title: "Password Manager"
    color: Theme.base

    readonly property bool mac: Qt.platform.os === "osx"
    readonly property int expanded: (Qt.ExpandedClientAreaHint || 0) | (Qt.NoTitleBarBackgroundHint || 0)
    // On macOS the liquid background runs under a transparent title bar, behind the window buttons.
    flags: mac && expanded ? (Qt.Window | expanded) : Qt.Window
    // Room for the window buttons, unless Qt already moved the content below the title bar.
    readonly property real topInset: mac && expanded && contentItem.y < 1 ? 26 : 0

    Component.onCompleted: {
        Theme.reduceMotion = Qt.binding(function () { return backend.reduceMotion })
        Theme.name = Qt.binding(function () { return backend.theme })
    }

    // The background covers the whole window, including the area under the transparent macOS
    // title bar, which newer Qt versions keep out of the content area.
    // Any empty spot moves the window (margins, gaps between panels, the top band, empty parts of the
    // sidebar); a double-click there zooms it, like a title bar. This is a MouseArea, not a DragHandler or
    // TapHandler: those also see presses that buttons, rows and lists have already taken, and would move or
    // zoom the window from them. startSystemMove hands the drag to the system on every platform.
    background: Item {
        LiquidBackground { anchors.fill: parent }
        MouseArea {
            objectName: "windowDrag"
            anchors.fill: parent
            property point pressedAt
            property bool moving: false
            onPressed: function (mouse) { pressedAt = Qt.point(mouse.x, mouse.y); moving = false }
            onPositionChanged: function (mouse) {
                if (pressed && !moving && Math.max(Math.abs(mouse.x - pressedAt.x), Math.abs(mouse.y - pressedAt.y)) > 3) {
                    moving = true
                    win.moveRequested()
                }
            }
            onDoubleClicked: win.visibility === Window.Maximized ? win.showNormal() : win.showMaximized()
        }
    }
    property int moveRequests: 0  // counted for the tests
    function moveRequested() {
        moveRequests++
        win.startSystemMove()
    }

    // macOS only allows resizing from a few pixels at the very edge, invisible against the gradient.
    // These bands make every edge and corner easy to grab. (Elsewhere the window keeps its normal frame.)
    component ResizeGrip: MouseArea {
        id: grip
        property int edges: 0
        property point pressedAt
        property rect startRect
        hoverEnabled: true
        preventStealing: true
        cursorShape: (edges === (Qt.LeftEdge | Qt.TopEdge) || edges === (Qt.RightEdge | Qt.BottomEdge)) ? Qt.SizeFDiagCursor
                   : (edges === (Qt.RightEdge | Qt.TopEdge) || edges === (Qt.LeftEdge | Qt.BottomEdge)) ? Qt.SizeBDiagCursor
                   : (edges & (Qt.LeftEdge | Qt.RightEdge)) ? Qt.SizeHorCursor : Qt.SizeVerCursor
        onPressed: function (mouse) {
            pressedAt = grip.mapToGlobal(mouse.x, mouse.y)
            startRect = Qt.rect(win.x, win.y, win.width, win.height)
        }
        onPositionChanged: function (mouse) {
            if (!pressed)
                return
            var now = grip.mapToGlobal(mouse.x, mouse.y)
            var dx = now.x - pressedAt.x, dy = now.y - pressedAt.y
            var r = startRect, x = r.x, y = r.y, w = r.width, h = r.height
            if (edges & Qt.RightEdge) w = Math.max(win.minimumWidth, r.width + dx)
            if (edges & Qt.LeftEdge) { w = Math.max(win.minimumWidth, r.width - dx); x = r.x + r.width - w }
            if (edges & Qt.BottomEdge) h = Math.max(win.minimumHeight, r.height + dy)
            if (edges & Qt.TopEdge) { h = Math.max(win.minimumHeight, r.height - dy); y = r.y + r.height - h }
            windowTools.setGeometry(win, Math.round(x), Math.round(y), Math.round(w), Math.round(h))
        }
    }
    Item {
        id: resizeGrips
        objectName: "resizeGrips"
        parent: win.contentItem
        anchors.fill: parent
        z: 1000
        visible: win.mac && win.visibility !== Window.FullScreen
        readonly property int band: 7
        readonly property int corner: 16
        ResizeGrip { objectName: "gripLeft"; edges: Qt.LeftEdge; x: 0; y: parent.corner; width: parent.band; height: parent.height - 2 * parent.corner }
        ResizeGrip { objectName: "gripRight"; edges: Qt.RightEdge; x: parent.width - parent.band; y: parent.corner; width: parent.band; height: parent.height - 2 * parent.corner }
        ResizeGrip { objectName: "gripTop"; edges: Qt.TopEdge; x: 90; y: 0; width: parent.width - 90 - parent.corner; height: 4 }
        ResizeGrip { objectName: "gripBottom"; edges: Qt.BottomEdge; x: parent.corner; y: parent.height - parent.band; width: parent.width - 2 * parent.corner; height: parent.band }
        // Top-left stays tiny: the window buttons sit just inside it.
        ResizeGrip { edges: Qt.LeftEdge | Qt.TopEdge; x: 0; y: 0; width: 5; height: 5 }
        ResizeGrip { edges: Qt.RightEdge | Qt.TopEdge; x: parent.width - parent.corner; y: 0; width: parent.corner; height: parent.corner }
        ResizeGrip { edges: Qt.LeftEdge | Qt.BottomEdge; x: 0; y: parent.height - parent.corner; width: parent.corner; height: parent.corner }
        ResizeGrip { objectName: "gripCorner"; edges: Qt.RightEdge | Qt.BottomEdge; x: parent.width - parent.corner; y: parent.height - parent.corner; width: parent.corner; height: parent.corner }
    }

    Item {
        id: scene
        anchors.fill: parent

        Loader {
            id: stage
            anchors.fill: parent
            sourceComponent: {
                switch (backend.stage) {
                case "loading": return loadingScreen
                case "fatal": return fatalScreen
                case "recoveryKey": return recoveryScreen
                case "main": return mainScreen
                default: return lockScreen
                }
            }
            onLoaded: { item.opacity = 0; fadeIn.restart() }
            NumberAnimation { id: fadeIn; target: stage.item; property: "opacity"; to: 1; duration: 420; easing.type: Easing.OutCubic }
        }
    }

    Component { id: loadingScreen; LoadingScreen {} }
    Component { id: fatalScreen; FatalScreen {} }
    Component { id: recoveryScreen; RecoveryKeyScreen {} }
    Component { id: lockScreen; LockScreen { mode: backend.stage } }
    Component { id: mainScreen; MainScreen { backdrop: scene; topInset: win.topInset } }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        maxWidth: Math.min(640, win.width - 120)
        z: 100
    }
    Connections {
        target: backend
        function onToast(message) { toast.show(message) }
        function onUndoable(message) { toast.show(message, "Undo", function () { backend.undo() }) }
    }
}
