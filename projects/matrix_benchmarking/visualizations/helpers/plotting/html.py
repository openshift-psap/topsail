from dash import html
from . import styles_css as css
from . import report


def info_card(title, items):
    """Create an information card with a list of key-value items.

    Args:
        title (str): The title of the information card.
        items (list): A list of tuples containing key-value pairs and their metadata.

    Returns:
        dash.html.Div: The HTML representation of the information card.
    """

    item_elements = []
    for key, value, is_last, is_highlight in items:
        value_element = value
        if is_highlight and isinstance(value, str):
            value_element = html.Span(value, style=css.STYLE_INFO_VALUE_HIGHLIGHT)

        item_style = css.STYLE_INFO_ITEM_LAST if is_last else css.STYLE_INFO_ITEM
        item_elements.append(
            html.Div([
                html.Div(f"{key}:", style=css.STYLE_INFO_KEY),
                html.Div(value_element, style=css.STYLE_INFO_VALUE)
            ], style=item_style)
        )

    return html.Div([
        html.Div(title, style=css.STYLE_INFO_CARD_HEADER),
        html.Div(item_elements, style=css.STYLE_INFO_CARD_BODY)
    ], style=css.STYLE_INFO_CARD)


def plot_card(plot_name, config):
    """Create a plot card with proper HTML structure.

    Args:
        plot_name (str): The name of the plot.
        config (dict): The configuration settings for the plot.

    Returns:
        dash.html.Div: The HTML representation of the plot card.
    """

    return html.Div([
        html.Div(
            html.Div(
                report.Plot_and_Text(plot_name, config),
                className='plot-container'
            ),
            style=css.STYLE_PLOT_CONTENT
        )
    ], style=css.STYLE_PLOT_CARD)
