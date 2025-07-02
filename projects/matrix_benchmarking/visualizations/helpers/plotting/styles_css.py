EMBEDDED_CSS = """
/* Base responsive container */
.report-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background-color: #f8f9fa;
    color: #343a40;
    padding: 2rem;
    width: 95%;
    max-width: 1400px;
    overflow-x: visible;
    margin: 0 auto;
}

/* Responsive styles for plots grid */
@media (max-width: 1024px) {
    .plots-grid-responsive {
        grid-template-columns: 1fr !important;
    }
}

/* Additional responsive styles for mobile */
@media (max-width: 768px) {
    .report-container {
        padding: 1rem !important;
        width: 95% !important;
    }
}

@media (max-width: 480px) {
    .info-card-header {
        font-size: 1rem !important;
        padding: 0.75rem 1rem !important;
    }

    .info-item {
        padding: 0.75rem 1rem !important;
    }

    .info-key {
        width: 100px !important;
        font-size: 0.85rem !important;
        padding-right: 0.5rem !important;
    }

    .info-value {
        font-size: 0.8rem !important;
    }

    .plot-content {
        padding: 1rem !important;
    }

    .plot-container {
        padding: 1rem !important;
    }

    .plot-container img {
        min-width: 300px !important;
        max-width: none !important;
        width: auto !important;
    }
}

/* Plot specific styling */
.plot-container {
    width: 100% !important;
    height: auto !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    padding: 2rem !important;
    overflow: visible !important;
}

.plot-container > div {
    width: 100% !important;
    height: auto !important;
}

.plot-container p {
    margin: 0 !important;
    width: 100% !important;
}

.plot-container a {
    display: block !important;
    width: 100% !important;
}

.plot-container img {
    max-width: none !important;
    width: auto !important;
    height: auto !important;
    display: block !important;
    object-fit: contain !important;
    margin: 0 auto !important;
    min-width: 600px !important;
}
"""

STYLE_CONTAINER = {
    'font-family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    'background-color': '#f8f9fa',
    'color': '#343a40',
    'padding': '2rem',
    'width': '95%',
    'max-width': '1400px',
    'overflow-x': 'visible',
    'margin': '0 auto'
}

STYLE_H1 = {
    'font-size': '2.5rem',
    'color': '#007BFF',
    'text-align': 'center',
    'margin-bottom': '2.5rem',
    'font-weight': '300'
}

STYLE_H2_SECTION = {
    'font-size': '1.75rem',
    'color': '#343a40',
    'border-bottom': '2px solid #dee2e6',
    'padding-bottom': '0.5rem',
    'margin': '2.5rem 0 1.5rem 0'
}

STYLE_INFO_CARD = {
    'background': 'white',
    'border': '1px solid #dee2e6',
    'border-radius': '8px',
    'box-shadow': '0 2px 8px rgba(0, 0, 0, 0.08)',
    'overflow': 'hidden',
    'display': 'flex',
    'flex-direction': 'column',
    'margin-bottom': '1rem'
}

STYLE_INFO_ROW = {
    'display': 'grid',
    'grid-template-columns': 'repeat(auto-fit, minmax(300px, 1fr))',
    'gap': '1.5rem',
    'margin-bottom': '2rem'
}

STYLE_INFO_CARD_HEADER = {
    'background': '#f8f9fa',
    'border-bottom': '1px solid #dee2e6',
    'padding': '1rem 1.25rem',
    'font-size': '1.1rem',
    'font-weight': '600',
    'color': '#007BFF'
}

STYLE_INFO_CARD_BODY = {
    'flex': '1',
    'padding': '0'
}

STYLE_INFO_ITEM = {
    'display': 'flex',
    'align-items': 'flex-start',
    'padding': '0.75rem 1.25rem',
    'border-bottom': '1px solid #f8f9fa',
    'min-height': '2.5rem'
}

STYLE_INFO_ITEM_LAST = {
    'display': 'flex',
    'align-items': 'flex-start',
    'padding': '0.75rem 1.25rem',
    'border-bottom': 'none',
    'min-height': '2.5rem'
}

STYLE_INFO_KEY = {
    'font-weight': '600',
    'color': '#495057',
    'width': '120px',
    'flex-shrink': '0',
    'font-size': '0.9rem',
    'text-align': 'left',
    'padding-right': '1rem'
}

STYLE_INFO_VALUE = {
    'font-family': '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',
    'font-size': '0.85rem',
    'color': '#343a40',
    'text-align': 'left',
    'flex': '1',
    'overflow-wrap': 'break-word',
    'word-break': 'break-word',
    'line-height': '1.4'
}

STYLE_INFO_VALUE_HIGHLIGHT = {
    'font-family': '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',
    'font-size': '1rem',
    'color': '#28a745',
    'text-align': 'left',
    'flex': '1',
    'overflow-wrap': 'break-word',
    'word-break': 'break-word',
    'line-height': '1.4',
    'font-weight': '600'
}

STYLE_PLOTS_GRID = {
    'display': 'grid',
    'grid-template-columns': '1fr',
    'gap': '3rem',
    'margin-bottom': '3rem',
    'padding': '1rem 0'
}

STYLE_PLOT_CARD = {
    'background': 'white',
    'border': '1px solid #dee2e6',
    'border-radius': '8px',
    'box-shadow': '0 2px 8px rgba(0, 0, 0, 0.08)',
    'overflow': 'visible',
    'width': '100%',
    'display': 'flex',
    'flex-direction': 'column',
    'margin-bottom': '2rem',
    'min-width': '0'
}

STYLE_PLOT_CONTENT = {
    'padding': '2rem',
    'width': '100%',
    'display': 'flex',
    'flex-direction': 'column',
    'align-items': 'center',
    'justify-content': 'flex-start',
    'overflow': 'visible'
}

STYLE_DETAILS = {
    'background': 'white',
    'border': '1px solid #dee2e6',
    'border-radius': '8px',
    'box-shadow': '0 2px 8px rgba(0, 0, 0, 0.08)',
    'overflow': 'hidden',
    'margin-bottom': '2rem'
}

STYLE_DETAILS_SUMMARY = {
    'background': '#f8f9fa',
    'padding': '1rem 1.25rem',
    'cursor': 'pointer',
    'font-weight': '600',
    'color': '#007BFF',
    'outline': 'none',
    'border': 'none'
}

STYLE_DETAILS_CONTENT = {
    'padding': '1.25rem'
}

STYLE_BENCHMARK_SECTION = {
    'margin-bottom': '2rem'
}

STYLE_JSON_PRE = {
    'background': '#2d3748',
    'color': '#e2e8f0',
    'padding': '1rem',
    'border-radius': '6px',
    'overflow-x': 'auto',
    'font-size': '0.8rem',
    'line-height': '1.5',
    'white-space': 'pre-wrap',
    'word-break': 'break-all'
}

STYLE_SMALL_TEXT = {
    'color': '#6c757d',
    'font-size': '0.8rem'
}

STYLE_H4 = {
    'margin-top': '1rem'
}
