#!/usr/bin/env bash
set -euo pipefail
task_dir=/mnt/f/Code/dell-5560-wall-mount/fusion/cfd/vendor/openfoam
expected=e6ddd89ed33131a4fc63460cb131ae7416a2a0062b590f4237121598626edf86
actual=$(sha256sum "$task_dir/pubkey.gpg" | cut -d' ' -f1)
test "$actual" = "$expected"
key=/usr/share/keyrings/dell5560-openfoam.gpg
source=/etc/apt/sources.list.d/dell5560-openfoam.list
preferences=/etc/apt/preferences.d/dell5560-openfoam
if test -e "$key" || test -e "$source" || test -e "$preferences"; then
    echo 'Task repository files already exist; inspect before changing.' >&2
    exit 1
fi
gpg --batch --dearmor --output "$key" "$task_dir/pubkey.gpg"
chmod 644 "$key"
cat > "$source" <<'EOF'
deb [arch=amd64 signed-by=/usr/share/keyrings/dell5560-openfoam.gpg] https://dl.openfoam.com/repos/deb noble main
EOF
cat > "$preferences" <<'EOF'
Package: *
Pin: origin dl.openfoam.com
Pin-Priority: 100

Package: openfoam*
Pin: origin dl.openfoam.com
Pin-Priority: 600
EOF
apt-get update -o Dir::Etc::sourcelist="$source" -o Dir::Etc::sourceparts=-
apt-cache policy openfoam2606-default openfoam2412-default openfoam2312-default
