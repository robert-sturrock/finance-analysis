import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dash_table
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from pymonzo import MonzoAPI
from monzo_app_functions import *


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
### Notes
# Currently showing the description is not necessarily logical
# Not built to handle multiple transactions per day. I don't know what
# current behaviour is showing

#### App starts ####
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Load data
df = monzo_data('eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJlYiI6IkZQb3d2OXZVdkhBMDc1TFZsQWFZIiwianRpIjoiYWNjdG9rXzAwMDA5Z28wRG9hYWhWRE5tZTQyNVoiLCJ0eXAiOiJhdCIsInYiOiI1In0.7KugZjRZ0jH89a_eYD0VjEIIlVaJOPqxxl-8JzctzGBp3aLOGINGplMhD1J0XIgtLoJZjiCJErzuPx7FnikM4Q')

# Re-categorise
df = category_assignment(df)

# Create dfs for table view and average spending chart
df_table = df[['date','amount','category','description','notes']]
df_dates = all_dates(df)

# Define categories
available_categories = df['category'].unique()

app.layout = html.Div([
    html.H1('Monzo Spending Dash', style={
            'textAlign': 'center', 'margin': '48px 0', 'fontFamily': 'system-ui'}),
    dcc.Tabs(id="tabs", children=[
        dcc.Tab(label='Overview', children=[
            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id='category',
                        options=[{'label': i, 'value': i} for i in available_categories],
                        value='eating_out',
                        multi=True
                    )
                ],
                style={'width': '100%', 'display': 'inline-block'}),
            ]),
            dcc.Graph(id='transact-graphic'),
            dcc.Graph(id='avg-graphic'),
            html.H2(children='Transation Details'),
            dash_table.DataTable(
                rows=df_table.to_dict('records'),
                row_selectable=True,
                filterable=True,
                sortable=True,
                selected_row_indices=[],
                id = 'dt_table'
            )
        ]),
        dcc.Tab(label='Spending/wealth summary', children=[
            html.H2("Wealth change over time"),
            html.Div([
                html.Div([
                    html.Label('Start Date'),
                    dcc.Input(
                        value='2019-01-01',
                        type='text',
                        id = 'start_date'),
                ]),
                html.Div([
                    html.Label('End Date'),
                    dcc.Input(
                        value=current_date(),
                        type='text',
                        id='end_date')
                ])
            ], style={'columnCount': 2}),
            dcc.Graph(id='wealth-graphic'),
            html.Div([
                    html.H4(children='Expense breakdown'),
                    dcc.Graph(id='expense-pie')
                ], style={'width':'60%', 'display': 'inline-block'}),
            html.Div([
                    html.H4(children='Income vs Expenses'),
                    dcc.Graph(id='expense-bar')
                ], style={'width':'40%', 'display': 'inline-block'})

        ]),
        dcc.Tab(label='Tab three', children=[
            html.Div([
                html.H1("This is the content in tab 3"),
            ])
        ]),
    ],
        style={
        'fontFamily': 'system-ui'
    },
        content_style={
        'borderLeft': '1px solid #d6d6d6',
        'borderRight': '1px solid #d6d6d6',
        'borderBottom': '1px solid #d6d6d6',
        'padding': '44px'
    },
        parent_style={
        'maxWidth': '1000px',
        'margin': '0 auto'
    }
    )
])


# Transaction Graph
@app.callback(
    dash.dependencies.Output('transact-graphic', 'figure'),
    [dash.dependencies.Input('category', 'value')]
    )
def update_graph(category):
    return transact_data(df, category)


# Avg Spend Graph
@app.callback(
    dash.dependencies.Output('avg-graphic', 'figure'),
    [dash.dependencies.Input('category', 'value')]
    )
def update_graph(category):
    return avg_spend(df_dates, category)

# Table output
@app.callback(
    dash.dependencies.Output('dt_table', 'rows'),
    [dash.dependencies.Input('category', 'value')])
def display_table(dropdown_value):
    if dropdown_value is None:
        return df_table.to_dict('records')
    else:
        dropdown_value = make_list(dropdown_value)
        tmp = df[df.category.isin(dropdown_value)]
        tmp = tmp.loc[:,["ymd",'amount','category','description']]
        return tmp.to_dict('records')

# Wealth Graph
@app.callback(
    dash.dependencies.Output('wealth-graphic', 'figure'),
    [dash.dependencies.Input('start_date', 'value'),
    dash.dependencies.Input('end_date', 'value')]
    )
def update_graph(start_date, end_date):
    return cum_wealth(df, start_date, end_date)

# Expense pie chart
@app.callback(
    dash.dependencies.Output('expense-pie', 'figure'),
    [dash.dependencies.Input('start_date', 'value'),
    dash.dependencies.Input('end_date', 'value')]
    )
def update_graph(start_date, end_date):
    return expense_pie(df, start_date, end_date)


# Wealth Graph
@app.callback(
    dash.dependencies.Output('expense-bar', 'figure'),
    [dash.dependencies.Input('start_date', 'value'),
    dash.dependencies.Input('end_date', 'value')]
    )
def update_graph(start_date, end_date):
    return income_expense(df, start_date, end_date)



if __name__ == '__main__':
    app.run_server(debug=True)
