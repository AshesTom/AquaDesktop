#!/bin/sh
# AquaDesktop — the Battery menu's "Using Significant Energy" list.
#
# Plasma launches every app in its own systemd unit under app.slice
# (app-[<launcher>-]<desktop id>[@…].service or …-<random>.scope, the XDG
# cgroup convention). Sample each unit's CPU time over two seconds and
# print, highest first, "<percent of one core>\t<name>\t<icon>" for apps at
# or above the threshold (first argument, default 20). Prints nothing when
# no app qualifies or the cgroup tree is unavailable. Read-only.
#
# SPDX-License-Identifier: GPL-3.0-or-later

threshold=${1:-20}
interval=2
slice=/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/app.slice
[ -d "$slice" ] || exit 0

# "<desktop id> <usage_usec>" per app unit; one app may own several units.
sample() {
    for unit in "$slice"/app-*.scope "$slice"/app-*.service; do
        # Autostart helpers are not apps the user opened.
        case $unit in *@autostart.service) continue ;; esac
        [ -r "$unit/cpu.stat" ] || continue
        id=${unit##*/}
        id=${id#app-}
        case $id in
            *.scope) id=${id%.scope}; id=${id%-*} ;;
            *) id=${id%.service}; id=${id%%@*} ;;
        esac
        # Dashes inside the id are escaped (\x2d): a bare one ends a launcher prefix.
        id=${id##*-}
        printf '%s %s\n' "$id" "$(sed -n 's/^usage_usec //p' "$unit/cpu.stat")"
    done | sed 's/\\x2d/-/g'
}

desktop_file() {
    data_dirs=${XDG_DATA_DIRS:-/usr/local/share:/usr/share}
    old_ifs=$IFS
    IFS=:
    for dir in "${XDG_DATA_HOME:-$HOME/.local/share}" $data_dirs; do
        if [ -r "$dir/applications/$1.desktop" ]; then
            IFS=$old_ifs
            printf '%s' "$dir/applications/$1.desktop"
            return
        fi
    done
    IFS=$old_ifs
}

# Name (localized when available) and Icon of the [Desktop Entry] group.
desktop_entry() {
    locale=${LC_ALL:-${LC_MESSAGES:-${LANG:-C}}}
    locale=${locale%%.*}
    locale=${locale%%@*}
    awk -F= -v full="$locale" -v short="${locale%%_*}" '
        /^\[/ { group = ($0 == "[Desktop Entry]"); next }
        !group { next }
        $1 == "Name[" full "]" { named_full = substr($0, index($0, "=") + 1) }
        $1 == "Name[" short "]" { named_short = substr($0, index($0, "=") + 1) }
        $1 == "Name" { name = substr($0, index($0, "=") + 1) }
        $1 == "Icon" { icon = substr($0, index($0, "=") + 1) }
        END {
            if (named_full != "") name = named_full
            else if (named_short != "") name = named_short
            printf "%s\t%s", name, icon
        }' "$1"
}

before=$(sample)
sleep "$interval"
after=$(sample)

printf '%s\n--\n%s\n' "$before" "$after" | awk -v threshold="$threshold" -v interval="$interval" '
    $0 == "--" { phase = 1; next }
    NF != 2 { next }
    !phase { start[$1] += $2; next }
    { end[$1] += $2 }
    END {
        for (id in end) {
            percent = (end[id] - start[id]) / (interval * 10000)
            if (percent >= threshold) printf "%d %s\n", percent, id
        }
    }' | sort -rn | head -n 5 | while read -r percent id; do
    file=$(desktop_file "$id")
    if [ -n "$file" ]; then
        entry=$(desktop_entry "$file")
        name=${entry%%	*}
        icon=${entry#*	}
    else
        name=$id
        icon=$id
    fi
    printf '%s\t%s\t%s\n' "$percent" "${name:-$id}" "${icon:-application-x-executable}"
done
