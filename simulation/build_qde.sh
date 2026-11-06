#!/bin/sh
# Builds qde_driver against the QCADesigner-E sources (https://github.com/FSillT/QCADesigner-E).
#   ./build_qde.sh /path/to/QCADesigner-E/QCADesignerE/src
# Needs GLib (brew install glib). Set SDK if the default macOS SDK fails to link.
set -e
SRC="$1"; HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SRC/coherence_vector_energy.c" ] || { echo "usage: $0 <QCADesignerE/src>"; exit 1; }
OBJ="fileio.c fileio_helpers.c custom_widgets.c simulation.c simulation_data.c bistable_simulation.c
 coherence_vector.c coherence_vector_energy.c design.c exp_array.c hsl2rgb.c generic_utils.c vector_table.c
 graph_dialog_widget_data.c objects/object_helpers.c objects/QCADCell.c objects/QCADCompoundDO.c
 objects/QCADDesignObject.c objects/QCADDOContainer.c objects/QCADLabel.c objects/QCADLayer.c
 objects/QCADRuler.c objects/QCADStretchyObject.c objects/QCADSubstrate.c"
FILES=""; for f in $OBJ; do FILES="$FILES $SRC/$f"; done
cc -O2 -w -std=gnu89 -fgnu89-inline ${SDK:+-isysroot "$SDK"} -DSTDIO_FILEIO \
   -DPACKAGE_DATA_DIR='""' -DPACKAGE_LOCALE_DIR='""' -DVERSION='"QDE"' -DPACKAGE='"QCADesignerE"' \
   -I"$SRC" -I"$SRC/.." $(pkg-config --cflags glib-2.0 gobject-2.0) -std=gnu99 \
   $FILES "$HERE/qde_driver.c" -o "${OUT:-$HERE/qde_driver}" $(pkg-config --libs glib-2.0 gobject-2.0) -lm
echo "built ${OUT:-$HERE/qde_driver}"
