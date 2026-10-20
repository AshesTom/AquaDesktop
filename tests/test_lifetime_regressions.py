"""Source guards for crash/lifetime fixes in bundled C++ and QML assets.

The container release run compiles the C++ components.  These focused guards
also pin the small control-flow conditions that caused the original bugs, so a
future source refresh cannot silently restore the unsafe forms while still
compiling successfully.
"""

from __future__ import annotations


def test_glass_decoration_region_survives_force_blur(repo):
    """Force blur splits a decorated window's frame into its content and its
    decoration, so the decoration keeps its own region (Better Blur DX)."""
    source = (repo / "src/offline/kwin-effects/better-blur-dx/src/window.cpp").read_text()
    assert "if (m_effectwindow->decoration()) {" in source
    assert "frame = content - BBDX::rectRoundedOut(m_effectwindow->contentsRect())" in source


def test_taskmanager_global_rect_checks_detached_items(repo):
    source = (repo / (
        "src/offline/plasmoids/org.kde.mac.tahoe.liquid.taskmanager/backend.cpp"
    )).read_text()
    body = source.split("QRect Backend::globalRect", 1)[1].split("\n}\n", 1)[0]

    assert "!item->window() || !item->parentItem()" in body
    assert body.index("!item->parentItem()") < body.index(
        "item->parentItem()->mapToScene")


def test_taskmanager_hover_timer_guards_destroyed_delegate(repo):
    source = (repo / (
        "src/offline/plasmoids/org.kde.mac.tahoe.liquid.taskmanager/"
        "contents/ui/MouseHandler.qml"
    )).read_text()
    timer = source.split("id: activationTimer", 1)[1].split(
        "WheelHandler {", 1,
    )[0]

    assert timer.index("if (!parent.hoveredItem)") < timer.index(
        "parent.hoveredItem.model.IsGroupParent")


def test_trash_rejects_non_file_drag_targets(repo):
    source = (repo / (
        "src/offline/plasmoids/org.kde.mac-tahoe-liquid-kde.trashcan/"
        "contents/ui/main.qml"
    )).read_text()
    entered = source.split("onDragEnter: event => {", 1)[1].split(
        "onDragLeave:", 1,
    )[0]

    assert "if (!dominated)" in entered
    assert "event.ignore();" in entered


def test_smartlauncher_count_is_assigned_once_after_full_range_check(repo):
    source = (repo / (
        "src/offline/plasmoids/org.kde.mac.tahoe.liquid.taskmanager/"
        "smartlauncherbackend.cpp"
    )).read_text()
    update = source.split("void Backend::update(", 1)[1].split(
        "void Backend::onServiceUnregistered", 1,
    )[0]

    assert update.count('properties.constFind(QStringLiteral("count"))') == 1
    assert "newCount >= std::numeric_limits<int>::min()" in update
    assert "newCount <= std::numeric_limits<int>::max()" in update
    assert 'updateLauncherProperty(\n        storageId, properties, QStringLiteral("count")' not in update
