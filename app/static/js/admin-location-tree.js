document.addEventListener(
    "DOMContentLoaded",
    () => {
        const tree = document.querySelector(
            ".location-tree"
        );

        const showTitle = tree
            ? tree.dataset.treeShowTitle
            : "Alárendelt helyek megjelenítése";

        const hideTitle = tree
            ? tree.dataset.treeHideTitle
            : "Alárendelt helyek elrejtése";

        const rows = Array.from(
            document.querySelectorAll(
                ".location-row[data-location-id]"
            )
        );

        if (!rows.length) {
            return;
        }

        const rowsById = new Map();

        rows.forEach(row => {
            rowsById.set(
                row.dataset.locationId,
                row
            );
        });

        const expanded = new Set();

        const isVisible = row => {
            const parentId =
                row.dataset.parentId;

            if (!parentId) {
                return true;
            }

            const parent =
                rowsById.get(parentId);

            if (!parent) {
                return true;
            }

            if (
                !expanded.has(parentId)
            ) {
                return false;
            }

            return isVisible(parent);
        };

        const refresh = () => {
            rows.forEach(row => {
                row.hidden = !isVisible(
                    row
                );

                const toggle =
                    row.querySelector(
                        ".location-tree-toggle"
                    );

                if (!toggle) {
                    return;
                }

                const id =
                    row.dataset.locationId;

                const isExpanded =
                    expanded.has(id);

                toggle.textContent =
                    isExpanded
                        ? "▼"
                        : "▶";

                toggle.setAttribute(
                    "aria-expanded",
                    isExpanded
                        ? "true"
                        : "false"
                );

                toggle.title =
                    isExpanded
                        ? hideTitle
                        : showTitle;
            });
        };

        rows.forEach(row => {
            const toggle =
                row.querySelector(
                    ".location-tree-toggle"
                );

            if (!toggle) {
                return;
            }

            toggle.addEventListener(
                "click",
                () => {
                    const id =
                        row.dataset.locationId;

                    if (
                        expanded.has(id)
                    ) {
                        expanded.delete(id);
                    } else {
                        expanded.add(id);
                    }

                    refresh();
                }
            );
        });

        const expandAll =
            document.getElementById(
                "location-tree-expand-all"
            );

        if (expandAll) {
            expandAll.addEventListener(
                "click",
                () => {
                    rows.forEach(row => {
                        if (
                            row.dataset
                                .hasChildren
                            === "1"
                        ) {
                            expanded.add(
                                row.dataset
                                    .locationId
                            );
                        }
                    });

                    refresh();
                }
            );
        }

        const collapseAll =
            document.getElementById(
                "location-tree-collapse-all"
            );

        if (collapseAll) {
            collapseAll.addEventListener(
                "click",
                () => {
                    expanded.clear();
                    refresh();
                }
            );
        }

        /*
         * Friss oldalbetöltés:
         * semmi nincs az expanded Setben,
         * tehát csak a gyökérelemek látszanak.
         */
        refresh();
    }
);
