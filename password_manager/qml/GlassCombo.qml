import QtQuick
import QtQuick.Controls.Basic
import "."

// Drop-down on glass. choices = [{label, value}].
ComboBox {
    id: control
    property var choices: []
    property int current: 0
    signal chosen(int value)
    model: choices
    textRole: "label"
    implicitWidth: 200
    implicitHeight: 38
    hoverEnabled: true
    currentIndex: Math.max(0, choices.findIndex(function (c) { return c.value === current }))
    onActivated: function (index) { chosen(choices[index].value) }
    font.pixelSize: 14

    background: Rectangle {
        radius: 12
        color: Qt.rgba(1, 1, 1, control.hovered ? 0.11 : 0.07)
        border.width: 1
        border.color: control.popup.visible ? Theme.accent : Theme.glassBorder
    }
    contentItem: Text {
        leftPadding: 14
        text: control.displayText
        font: control.font
        color: Theme.text
        verticalAlignment: Text.AlignVCenter
    }
    indicator: Icon {
        name: "chevron"
        size: 14
        color: Theme.secondary
        rotation: control.popup.visible ? -90 : 90
        x: control.width - width - 14
        anchors.verticalCenter: parent.verticalCenter
        Behavior on rotation { NumberAnimation { duration: 180 } }
    }
    delegate: ItemDelegate {
        width: control.width - 8
        height: 34
        highlighted: control.highlightedIndex === index
        contentItem: Text {
            text: modelData.label
            color: Theme.text
            font.pixelSize: 14
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 9
            color: parent.highlighted ? Theme.tint(Theme.accent, 0.35) : "transparent"
        }
    }
    popup: Popup {
        y: control.height + 6
        width: control.width
        padding: 4
        implicitHeight: contentItem.implicitHeight + 8
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
            NumberAnimation { property: "scale"; from: 0.94; to: 1; duration: 200; easing.type: Easing.OutBack }
        }
        contentItem: ListView {
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            interactive: false
            spacing: 2
        }
        background: Rectangle {
            radius: 13
            color: Theme.glassStrong
            border.width: 1
            border.color: Theme.glassBorder
        }
    }
}
