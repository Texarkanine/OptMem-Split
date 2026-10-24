#!/bin/sh
# OptMem installer. Run it again to update: it replaces the tool and
# relink-path-stores, and `memo init` never touches memories that already exist.
#
#   curl -fsSL https://raw.githubusercontent.com/Texarkanine/OptMem-Split/main.split/install.sh | sh

set -e
DIR="$HOME/.optmem"

command -v python3 >/dev/null || {
  echo "OptMem is one Python file, and this machine has no python3." >&2
  echo "Install python3, then run this line again." >&2
  exit 1
}

mkdir -p "$DIR"
curl -fsSL https://raw.githubusercontent.com/Texarkanine/OptMem-Split/main.split/memo -o "$DIR/memo.new"
mv "$DIR/memo.new" "$DIR/memo"
chmod +x "$DIR/memo"
curl -fsSL https://raw.githubusercontent.com/Texarkanine/OptMem-Split/main.split/relink-path-stores -o "$DIR/relink-path-stores.new"
mv "$DIR/relink-path-stores.new" "$DIR/relink-path-stores"
chmod +x "$DIR/relink-path-stores"

echo "Path-local stores follow the resolved directory."
echo "To see stores that would move, run: $DIR/relink-path-stores"
echo "That command writes nothing unless you add --move."

exec "$DIR/memo" init
