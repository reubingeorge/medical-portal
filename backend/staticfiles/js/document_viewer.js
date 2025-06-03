/**
 * PDF.js Canvas Renderer - Optimized
 * Properly configured for cross-origin restrictions and WebWorker issues
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("[PDF Viewer] Initializing...");

    // Get the PDF container element
    const pdfContainer = document.getElementById('pdf-viewer');
    if (!pdfContainer) {
        console.error("[PDF Viewer] Error: PDF container element not found");
        return;
    }

    const pdfUrl = pdfContainer.getAttribute('data-pdf-url');
    if (!pdfUrl) {
        console.error("[PDF Viewer] Error: No PDF URL provided");
        return;
    }

    console.log("[PDF Viewer] PDF URL:", pdfUrl);

    // Configure viewer HTML with simpler, more reliable structure
    pdfContainer.innerHTML = `
        <div class="flex flex-col h-full">
            <!-- Loading indicator -->
            <div id="pdf-loading" class="flex items-center justify-center h-full" >
                <div class="text-center">
                    <svg class="animate-spin h-10 w-10 text-blue-500 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <p class="text-gray-600">Loading PDF...</p>
                </div>
            </div>
            
            <!-- PDF canvas container -->
            <div id="canvas-wrapper" class="bg-white rounded-lg shadow-md w-full flex justify-center" style="display: none; height: calc(100vh - 150px); max-height: 1200px;">
                <div id="canvas-container" class="overflow-y-auto overflow-x-hidden p-2 w-full h-full flex justify-center">
                    <canvas id="pdf-canvas" class="shadow border border-gray-200"></canvas>
                </div>
            </div>
            
            <!-- Error display -->
            <div id="pdf-error" class="flex items-center justify-center h-full" style="display: none;">
                <div class="text-center p-6">
                    <svg class="h-12 w-12 text-red-500 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <p id="error-message" class="text-red-600 font-medium">Failed to load PDF</p>
                    <p id="error-details" class="text-gray-600 text-sm mt-2"></p>
                    <div class="mt-6 flex justify-center space-x-4">
                        <a href="${pdfUrl}" target="_blank" class="inline-flex items-center px-4 py-2 text-sm font-medium rounded text-white bg-blue-600 hover:bg-blue-700">
                            <svg class="h-4 w-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                            Open in New Tab
                        </a>
                        <a href="${pdfUrl}" download class="inline-flex items-center px-4 py-2 text-sm font-medium rounded text-gray-700 bg-gray-200 hover:bg-gray-300">
                            <svg class="h-4 w-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                            Download
                        </a>
                    </div>
                </div>
            </div>
            
            <!-- Controls -->
            <div class="flex justify-center mt-4 mb-14 items-center w-full px-4" id="pdf-controls" style="display: none; margin-bottom: 3.5rem;">
                <div class="flex space-x-2 mx-auto">
                    <button id="prev-page" class="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50" disabled>
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
                        </svg>
                    </button>
                    <div class="text-sm text-gray-600 flex items-center whitespace-nowrap">
                        Page <span id="page-num" class="mx-1">0</span> of <span id="page-count" class="mx-1">0</span>
                    </div>
                    <button id="next-page" class="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50" disabled>
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    `;

    // Load the PDF using PDF.js directly (skip iframe attempt since we know it will fail due to X-Frame-Options)
    loadPdfJs();

    function loadPdfJs() {
        console.log("[PDF Viewer] Loading PDF.js...");

        // Function to load scripts
        function loadScript(url, callback) {
            console.log("[PDF Viewer] Loading script:", url);
            const script = document.createElement('script');
            script.src = url;
            script.onload = callback;
            script.onerror = function() {
                console.error("[PDF Viewer] Failed to load script:", url);
                showError("Failed to load PDF viewer components");
            };
            document.head.appendChild(script);
        }

        // First load PDF.js
        loadScript('/static/js/pdfjs/pdf.min.js', function() {
            // Configure PDF.js to use the worker in the current origin
            // This should help with the "Setting up fake worker" warning
            window['pdfjs-dist/build/pdf'].GlobalWorkerOptions.workerSrc = '/static/js/pdfjs/pdf.worker.min.js';
            initPdfJs();
        });
    }

    function initPdfJs() {
        console.log("[PDF Viewer] Initializing PDF.js renderer");

        // Access the PDF.js library
        const pdfjsLib = window['pdfjs-dist/build/pdf'];
        if (!pdfjsLib) {
            console.error("[PDF Viewer] PDF.js library not found");
            showError("PDF.js library failed to initialize");
            return;
        }

        // Get UI elements
        const loadingDiv = document.getElementById('pdf-loading');
        const canvasWrapper = document.getElementById('canvas-wrapper');
        const canvasContainer = document.getElementById('canvas-container');
        const canvas = document.getElementById('pdf-canvas');
        const controls = document.getElementById('pdf-controls');
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        const pageNumSpan = document.getElementById('page-num');
        const pageCountSpan = document.getElementById('page-count');

        // Make sure we found all the elements
        if (!canvas || !loadingDiv || !canvasWrapper || !prevButton || !nextButton) {
            console.error("[PDF Viewer] Missing required UI elements");
            showError("Internal error: Missing UI elements");
            return;
        }

        // Variables to track state
        let pdfDoc = null;
        let pageNum = 1;
        let pageRendering = false;
        let pageNumPending = null;
        let scale = 1.0;

        // Get the 2D rendering context
        const ctx = canvas.getContext('2d');
        if (!ctx) {
            console.error("[PDF Viewer] Could not get canvas context");
            showError("Your browser doesn't support canvas rendering");
            return;
        }

        console.log("[PDF Viewer] Fetching PDF from URL:", pdfUrl);

        // Try to fetch the PDF directly
        fetch(pdfUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                console.log("[PDF Viewer] PDF fetched successfully, processing...");
                return response.arrayBuffer();
            })
            .then(arrayBuffer => {
                // Load the PDF with PDF.js
                console.log("[PDF Viewer] PDF data received, loading with PDF.js...");
                const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
                return loadingTask.promise;
            })
            .then(pdf => {
                console.log("[PDF Viewer] PDF document loaded successfully, pages:", pdf.numPages);
                pdfDoc = pdf;
                pageCountSpan.textContent = pdf.numPages;

                // Enable buttons if there are multiple pages
                if (pdf.numPages > 1) {
                    nextButton.disabled = false;
                }

                // Show the canvas container and controls
                loadingDiv.style.display = 'none';
                canvasWrapper.style.display = 'block';
                controls.style.display = 'flex';

                // Render the first page
                renderPage(pageNum);

                // Add event listeners for controls
                prevButton.addEventListener('click', onPrevPage);
                nextButton.addEventListener('click', onNextPage);

                // Add keyboard navigation
                document.addEventListener('keydown', function(e) {
                    // Only process if the PDF viewer is in focus (approximated by canvas being visible)
                    if (canvasWrapper.style.display === 'block') {
                        if (e.key === 'ArrowLeft' && !prevButton.disabled) {
                            onPrevPage();
                        } else if (e.key === 'ArrowRight' && !nextButton.disabled) {
                            onNextPage();
                        }
                    }
                });
            })
            .catch(error => {
                console.error("[PDF Viewer] Error loading PDF:", error);
                showError("Failed to load PDF", error.message);
            });

        // Render a specific page
        function renderPage(num) {
            pageRendering = true;
            console.log(`[PDF Viewer] Rendering page ${num} at scale ${scale}`);

            // Update page counters
            pageNumSpan.textContent = num;

            // Update buttons
            prevButton.disabled = num <= 1;
            nextButton.disabled = num >= pdfDoc.numPages;

            // Get the page
            pdfDoc.getPage(num).then(page => {
                console.log("[PDF Viewer] Page loaded, rendering...");

                // Get the original viewport at scale 1.0
                const originalViewport = page.getViewport({ scale: 1.0 });

                // Calculate the container dimensions
                const containerWidth = canvasContainer.clientWidth - 20; // account for padding

                // Calculate scaling factor to fit width properly
                const widthScale = containerWidth / originalViewport.width;

                // Apply user's zoom level to the calculated scale
                const finalScale = Math.min(widthScale, 1.5) * scale; // Cap at 1.5x for readability

                // Get the viewport with the calculated scale
                const viewport = page.getViewport({ scale: finalScale });

                // Set canvas dimensions to match page with scale
                canvas.height = viewport.height;
                canvas.width = viewport.width;

                // Make sure canvas wrapper adjusts to content
                //canvasWrapper.style.minHeight = canvas.height + 'px';

                // Render PDF page into canvas context
                const renderContext = {
                    canvasContext: ctx,
                    viewport: viewport
                };

                const renderTask = page.render(renderContext);

                renderTask.promise.then(() => {
                    console.log("[PDF Viewer] Page rendered successfully");
                    pageRendering = false;

                    // Check if there's a pending page
                    if (pageNumPending !== null) {
                        renderPage(pageNumPending);
                        pageNumPending = null;
                    }
                }).catch(error => {
                    console.error("[PDF Viewer] Error rendering page:", error);
                    pageRendering = false;
                    showError("Error rendering PDF page", error.message);
                });
            }).catch(error => {
                console.error("[PDF Viewer] Error getting page:", error);
                pageRendering = false;
                showError("Error loading PDF page", error.message);
            });
        }

        // Queue a page rendering if one is already in progress
        function queueRenderPage(num) {
            if (pageRendering) {
                pageNumPending = num;
            } else {
                renderPage(num);
            }
        }

        // Navigation functions
        function onPrevPage() {
            if (pageNum <= 1) return;
            pageNum--;
            queueRenderPage(pageNum);
        }

        function onNextPage() {
            if (pageNum >= pdfDoc.numPages) return;
            pageNum++;
            queueRenderPage(pageNum);
        }
    }

    // Show error message
    function showError(message, details = '') {
        console.error("[PDF Viewer] Error:", message, details);

        const loadingDiv = document.getElementById('pdf-loading');
        const canvasWrapper = document.getElementById('canvas-wrapper');
        const controls = document.getElementById('pdf-controls');
        const errorDiv = document.getElementById('pdf-error');
        const errorMessageEl = document.getElementById('error-message');
        const errorDetailsEl = document.getElementById('error-details');

        if (loadingDiv) loadingDiv.style.display = 'none';
        if (canvasWrapper) canvasWrapper.style.display = 'none';
        if (controls) controls.style.display = 'none';

        if (errorDiv && errorMessageEl) {
            errorMessageEl.textContent = message;
            if (details && errorDetailsEl) {
                errorDetailsEl.textContent = details;
            }
            errorDiv.style.display = 'flex';
        }
    }
});