pragma Singleton
import QtQuick

// Colours, type and motion shared by every screen. A dark "liquid glass" look on all platforms,
// in one of four colour themes; each theme is five colours that flow through the background.
QtObject {
    id: theme
    property string name: "aurora"
    property bool reduceMotion: false

    readonly property var palettes: ({
        "aurora": { "colors": ["#4B3BFF", "#B23BFF", "#FF3B8E", "#1FB6FF", "#18D9A0"],
                    "accent": "#8B7BFF", "accent2": "#E15CFF", "accent3": "#4FD1FF", "label": "Aurora" },
        "ocean":  { "colors": ["#1238FF", "#1FA2FF", "#12D8C3", "#5B3BFF", "#3BE8FF"],
                    "accent": "#3BA9FF", "accent2": "#2EE6C5", "accent3": "#7AD7FF", "label": "Ocean" },
        "sunset": { "colors": ["#FF5A1F", "#FF2E7E", "#B82EFF", "#FFB01F", "#FF6F61"],
                    "accent": "#FF7A59", "accent2": "#FF3D9A", "accent3": "#FFC15C", "label": "Sunset" },
        "forest": { "colors": ["#0F9D58", "#2BD47D", "#0FB5A6", "#7CD420", "#1E6F9C"],
                    "accent": "#2BD47D", "accent2": "#16C1B0", "accent3": "#A6F05A", "label": "Forest" }
    })
    readonly property var palette: palettes[name] || palettes["aurora"]
    readonly property var themeNames: ["aurora", "ocean", "sunset", "forest"]

    readonly property color c1: palette.colors[0]
    readonly property color c2: palette.colors[1]
    readonly property color c3: palette.colors[2]
    readonly property color c4: palette.colors[3]
    readonly property color c5: palette.colors[4]
    readonly property color accent: palette.accent
    readonly property color accent2: palette.accent2
    readonly property color accent3: palette.accent3

    readonly property color base: "#07070D"
    readonly property color text: "#F5F5FA"
    readonly property color secondary: Qt.rgba(1, 1, 1, 0.66)
    readonly property color tertiary: Qt.rgba(1, 1, 1, 0.42)
    readonly property color glass: Qt.rgba(1, 1, 1, 0.07)
    readonly property color glassInner: Qt.rgba(1, 1, 1, 0.06)
    readonly property color glassStrong: Qt.rgba(0.07, 0.07, 0.12, 0.84)
    readonly property color glassBorder: Qt.rgba(1, 1, 1, 0.14)
    readonly property color hover: Qt.rgba(1, 1, 1, 0.07)
    readonly property color danger: "#FF6B8B"
    readonly property color warning: "#FFB35C"
    readonly property color success: "#4BE3A2"
    readonly property color star: "#FFD25C"
    readonly property string mono: Qt.platform.os === "osx" ? "Menlo"
                                   : Qt.platform.os === "windows" ? "Consolas" : "DejaVu Sans Mono"
    readonly property int radius: 22

    function tint(c, alpha) { return Qt.rgba(c.r, c.g, c.b, alpha) }
    function strengthColor(score) {
        return score < 0 ? tertiary : [danger, danger, warning, success, success][score]
    }
}
