document.addEventListener(
    "DOMContentLoaded",
    () => {
        const viewer = document.getElementById(
            "item-image-viewer"
        );

        if (!viewer) {
            return;
        }

        const viewerImage =
            viewer.querySelector(
                ".item-image-viewer-image"
            );

        const closeButton =
            viewer.querySelector(
                ".item-image-viewer-close"
            );

        const closeViewer = () => {
            viewer.hidden = true;
            viewerImage.src = "";
        };

        document
            .querySelectorAll(
                ".item-image-button"
            )
            .forEach(button => {
                button.addEventListener(
                    "click",
                    () => {
                        viewerImage.src =
                            button.dataset.imageSrc;

                        viewer.hidden = false;
                    }
                );
            });

        closeButton.addEventListener(
            "click",
            closeViewer
        );

        viewer.addEventListener(
            "click",
            event => {
                if (event.target === viewer) {
                    closeViewer();
                }
            }
        );

        document.addEventListener(
            "keydown",
            event => {
                if (
                    event.key === "Escape"
                    && !viewer.hidden
                ) {
                    closeViewer();
                }
            }
        );
    }
);
