import QtQuick
import QtQuick.Shapes
import "."

// Line icons drawn from SVG paths on a 24x24 grid, so they stay sharp at any size.
Item {
    id: root
    property string name: ""
    property color color: Theme.text
    property real size: 18
    property real lineWidth: 1.8
    property bool filled: false
    width: size
    height: size

    readonly property var paths: ({
        "key": "M4 12a4 4 0 1 0 8 0a4 4 0 1 0 -8 0 M12 12h9 M17 12v3 M20.5 12v2.2",
        "star": "M12 3.5l2.6 5.3 5.9.9-4.25 4.15 1 5.85L12 16.95 6.75 19.7l1-5.85L3.5 9.7l5.9-.9z",
        "warning": "M12 4L2.8 19.5h18.4z M12 10v4.5 M12 17.3v.2",
        "reused": "M9 9h10.5v10.5H9z M15 9V4.5H4.5V15H9",
        "trash": "M4 7h16 M9 7V4.5h6V7 M6.5 7l1 13h9l1-13 M10 11v5.5 M14 11v5.5",
        "gear": "M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6z M12 2.5v3 M12 18.5v3 M2.5 12h3 M18.5 12h3 M5.3 5.3l2.1 2.1 M16.6 16.6l2.1 2.1 M5.3 18.7l2.1-2.1 M16.6 7.4l2.1-2.1",
        "lock": "M6 11h12v9H6z M8.5 11V8a3.5 3.5 0 0 1 7 0v3",
        "plus": "M12 5v14 M5 12h14",
        "search": "M10.5 4a6.5 6.5 0 1 0 0 13a6.5 6.5 0 1 0 0-13z M15.5 15.5L20 20",
        "copy": "M9 9h11v11H9z M15 9V4H4v11h5",
        "eye": "M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12z M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6z",
        "eyeOff": "M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12z M4 4l16 16",
        "sparkle": "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z",
        "external": "M14 4h6v6 M20 4l-9 9 M18 14v6H4V6h6",
        "check": "M5 12.5l4.5 4.5L19 7.5",
        "close": "M6 6l12 12 M18 6L6 18",
        "edit": "M4 20h4L19 9l-4-4L4 16z M14 6l4 4",
        "restore": "M4.5 12a7.5 7.5 0 1 0 2.2-5.3 M4.5 4v4.5H9",
        "shield": "M12 3l7 3v6c0 4.5-3 7.5-7 9c-4-1.5-7-4.5-7-9V6z M9 12l2 2 4-4",
        "import": "M12 4v11 M7.5 10.5L12 15l4.5-4.5 M5 19.5h14",
        "export": "M12 15V4 M7.5 8.5L12 4l4.5 4.5 M5 19.5h14",
        "chevron": "M9 6l6 6-6 6",
        "timer": "M12 21a8 8 0 1 0 0-16a8 8 0 1 0 0 16z M12 9v4.5l2.8 1.8 M9.5 2.5h5",
        "note": "M6 3h9l4 4v14H6z M14 3v5h5 M9 12.5h7 M9 16.5h5",
        "clock": "M12 21a9 9 0 1 0 0-18a9 9 0 1 0 0 18z M12 7v5l3.5 2",
        "leak": "M8.2 3h7.6L21 8.2v7.6L15.8 21H8.2L3 15.8V8.2z M12 8v5 M12 16.3v.2",
        "sort": "M7 4v16 M3.5 16.5L7 20l3.5-3.5 M17 20V4 M13.5 7.5L17 4l3.5 3.5",
        "archive": "M4 8h16v12H4z M3 4h18v4H3z M10 12h4",
        "mail": "M3.5 5.5h17v13h-17z M4 6.5l8 6.2 8-6.2",
        "command": "M9 9V6.5a2.5 2.5 0 1 0-2.5 2.5H9z M15 9h2.5A2.5 2.5 0 1 0 15 6.5V9z M9 15H6.5A2.5 2.5 0 1 0 9 17.5V15z M15 15v2.5a2.5 2.5 0 1 0 2.5-2.5H15z M9 9h6v6H9z",
        "palette": "M12 3a9 9 0 1 0 0 18c1.2 0 1.8-.8 1.8-1.7 0-.5-.2-.9-.5-1.2-.3-.3-.5-.7-.5-1.2 0-.9.8-1.7 1.7-1.7H17a4 4 0 0 0 4-4C21 6.7 17 3 12 3z M7.5 11.5v.2 M10 7.5v.2 M14.5 7.5v.2"
    })

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        transform: Scale { xScale: root.size / 24; yScale: root.size / 24 }
        ShapePath {
            strokeColor: root.color
            strokeWidth: root.lineWidth
            fillColor: root.filled ? root.color : "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths[root.name] || "" }
        }
    }
}
