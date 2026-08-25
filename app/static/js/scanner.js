(() => {
    "use strict";

    const startButton = document.getElementById(
        "start-camera"
    );

    const stopButton = document.getElementById(
        "stop-camera"
    );

    const videoWrap = document.getElementById(
        "scanner-video-wrap"
    );

    const video = document.getElementById(
        "scanner-video"
    );

    const status = document.getElementById(
        "scanner-camera-status"
    );

    const codeInput = document.getElementById(
        "scanner-code"
    );

    const form = document.getElementById(
        "scanner-form"
    );

    let stream = null;
    let detector = null;
    let scanning = false;
    let scanTimer = null;
    let lastDetectedCode = "";
    let lastDetectedAt = 0;

    const supportedFormats = [
        "code_128",
        "code_39",
        "code_93",
        "codabar",
        "ean_13",
        "ean_8",
        "itf",
        "upc_a",
        "upc_e",
        "qr_code",
        "data_matrix",
    ];

    function setStatus(message) {
        status.textContent = message;
    }

    function stopScanTimer() {
        if (scanTimer !== null) {
            clearTimeout(scanTimer);
            scanTimer = null;
        }
    }

    function stopCamera() {
        scanning = false;

        stopScanTimer();

        if (stream !== null) {
            for (const track of stream.getTracks()) {
                track.stop();
            }

            stream = null;
        }

        video.srcObject = null;

        videoWrap.hidden = true;
        stopButton.hidden = true;
        startButton.hidden = false;

        setStatus(
            "A kamera leállítva."
        );
    }

    function submitDetectedCode(rawValue) {
        const value = String(
            rawValue || ""
        ).trim();

        if (!value) {
            return;
        }

        const now = Date.now();

        if (
            value === lastDetectedCode
            && now - lastDetectedAt < 2000
        ) {
            return;
        }

        lastDetectedCode = value;
        lastDetectedAt = now;

        scanning = false;

        codeInput.value = value;

        setStatus(
            `Kód felismerve: ${value}`
        );

        stopCamera();

        window.setTimeout(
            () => {
                if (
                    typeof form.requestSubmit
                    === "function"
                ) {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            },
            150
        );
    }

    async function detectOnce() {
        if (
            !scanning
            || detector === null
        ) {
            return;
        }

        try {
            const results = await detector.detect(
                video
            );

            if (
                Array.isArray(results)
                && results.length > 0
            ) {
                const firstResult = results[0];

                if (
                    firstResult
                    && firstResult.rawValue
                ) {
                    submitDetectedCode(
                        firstResult.rawValue
                    );

                    return;
                }
            }

        } catch (error) {
            console.error(
                "Vonalkódfelismerési hiba:",
                error
            );
        }

        if (scanning) {
            scanTimer = window.setTimeout(
                detectOnce,
                200
            );
        }
    }

    async function createDetector() {
        if (
            !("BarcodeDetector" in window)
        ) {
            throw new Error(
                "A böngésző nem támogatja "
                + "a BarcodeDetector API-t."
            );
        }

        let formats = supportedFormats;

        if (
            typeof BarcodeDetector
                .getSupportedFormats
            === "function"
        ) {
            const browserFormats =
                await BarcodeDetector
                    .getSupportedFormats();

            formats = supportedFormats.filter(
                format =>
                    browserFormats.includes(
                        format
                    )
            );
        }

        if (formats.length === 0) {
            throw new Error(
                "A böngésző nem támogat "
                + "használható vonalkódformátumot."
            );
        }

        return new BarcodeDetector({
            formats,
        });
    }

    async function startCamera() {
        if (stream !== null) {
            return;
        }

        if (
            !navigator.mediaDevices
            || !navigator.mediaDevices
                .getUserMedia
        ) {
            setStatus(
                "Ez a böngésző nem támogatja "
                + "a kamerahasználatot."
            );

            return;
        }

        startButton.disabled = true;

        setStatus(
            "Kamera indítása..."
        );

        try {
            detector = await createDetector();

            stream =
                await navigator.mediaDevices
                    .getUserMedia({
                        video: {
                            facingMode: {
                                ideal: "environment",
                            },
                            width: {
                                ideal: 1280,
                            },
                            height: {
                                ideal: 720,
                            },
                        },
                        audio: false,
                    });

            video.srcObject = stream;

            await video.play();

            videoWrap.hidden = false;
            stopButton.hidden = false;
            startButton.hidden = true;

            scanning = true;

            setStatus(
                "Irányítsd a kamerát "
                + "a vonalkódra."
            );

            detectOnce();

        } catch (error) {
            console.error(
                "Scanner indítási hiba:",
                error
            );

            stopCamera();

            if (
                error
                && error.name
                === "NotAllowedError"
            ) {
                setStatus(
                    "A kamera használata "
                    + "nincs engedélyezve."
                );

            } else if (
                error
                && error.name
                === "NotFoundError"
            ) {
                setStatus(
                    "Nem található használható kamera."
                );

            } else {
                setStatus(
                    error?.message
                    || "A kamera nem indítható."
                );
            }
        } finally {
            startButton.disabled = false;
        }
    }

    startButton.addEventListener(
        "click",
        startCamera
    );

    stopButton.addEventListener(
        "click",
        stopCamera
    );

    window.addEventListener(
        "pagehide",
        stopCamera
    );
})();
