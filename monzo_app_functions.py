import datetime as dt
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dash_table
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from pymonzo import MonzoAPI


#### Create functions ####
def generate_table(dataframe, max_rows=10):
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +

        # Body
        [html.Tr([
            html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
        ]) for i in range(min(len(dataframe), max_rows))],
         style={'width':'90%'}
    )

# Turn object into a list if not currently a list
def make_list(item):
  return(item if isinstance(item, list) else [item])


# Get current date
def current_date():
 return dt.datetime.today().strftime("%Y-%m-%d")


### Load in data from API
def monzo_data(access_token):
    '''
    Used to access the monzo api and return a dataframe with relevant information
    Currently relies on pymonzo and the use of a developer ID token.
    '''
    # Access API
    monzo_api = MonzoAPI(access_token)

    # Create dataframe base
    df = pd.DataFrame()
    descriptions = []
    amounts = []
    categories = []
    notes = []
    dates = []

    # Get transactions
    for transaction in monzo_api.transactions(account_id = monzo_api.accounts()[1].id):
        descriptions.append(transaction.description)
        amounts.append(transaction.amount)
        categories.append(transaction.category)
        notes.append(transaction.notes)
        dates.append(transaction.created)

    # Create dataframe
    df['description'] = descriptions
    df['amount'] = amounts
    df['category'] = categories
    df['date'] = dates
    df['notes'] = notes

    # Convert all amounts to dollars
    df['amount'] = df['amount']/100

    # Modify date object
    df['ymd'] = df['date'].apply(lambda x:
                                    dt.datetime.date(x))

    return df

# Reclassify into categories
# Impliment simple changes
def category_assignment(df):
  '''This function assigns categories where the category value
  is not available. It follows fairly simple rules. Currently
  implimented ones are:

  1.Transfer to and Transfer from are assigned 'transfer'
  2.a 16 string number is 'general'
  3.Funding C is 'transfer'
  4.>2000 income is salary (if not also transfer)
  5.Faster payments is asigned to entertainment
  6.If notes contains funding cirlce then modify to Transfer


  For more general audiences adding the following tags will flag transfer:
  1. #saving (as we want to flag transfers that not associated with a reduction in wealth)
  '''
  # Bulk classification
  df.loc[(df.amount > 1500), 'category'] = 'salary' # start with this and reclassify as needed
  df.loc[df.description.str.contains("pot_"), 'category'] = 'transfer' # transfers
  df.loc[df.description.str.contains("Transfer to|Transfer from"), 'category'] = 'transfer' # transfers
  df.loc[(df.description.str.contains("Maria Lachenauer") & (df.amount < 0)), 'category'] = 'transfer' # Isabel transfers
  df.loc[(df.description.str.contains("Robert Sturrock") & (df.amount < 0)), 'category'] = 'transfer' # Isabel transfers
  df.loc[df.description.str.match("\d{16}"), 'category'] = 'general' # credit card
  df.loc[df.description.str.contains("FUNDING C"), 'category'] = 'transfer' # funding circle
  df.loc[(df.description.str.match("VG\d{16}")) | (df.description.str.match("VANGAURD")), 'category'] = 'transfer' # vangaurd
  df.loc[(df.description.str.contains("Faster Payments")) & (df.amount < abs(500)), 'category'] = 'general' # payments to others

  # Tag specifics
  df.loc[df.description.str.contains("#savings"), 'category'] = 'transfer'
  df.loc[df.notes.str.contains("#saving"), 'category'] = 'transfer'
  df.loc[df.description.str.contains("#google"), 'category'] = 'transfer'


  # This is replacing just the nulls
  df.loc[(pd.isnull(df.category)), 'category'] = 'general'
  return df

# Create all dates version of table
def all_dates(df):
    # Create a date range
    all_dates = pd.DataFrame({'ymd': pd.date_range(start='1/1/2018', end=current_date())})
    all_dates['dummy'] = 1
    all_dates['ymd'] = all_dates['ymd'].apply(lambda x:
                                                dt.datetime.date(x))
    # Create all categories
    categories = df['category'].unique()
    categories = categories[categories != 'NaN']
    all_categories = pd.DataFrame({'category':categories})
    all_categories['dummy'] = 1

    # Create all dates and categories
    df_dates = pd.merge(all_dates, all_categories, how='outer', on = 'dummy')

    # Join data to actuals
    df_dates = pd.merge(df_dates, df, how='left', on = ['ymd','category'])

    # Change all NaN in amount to 0s, note the use of "inplace=True"
    df_dates['amount'].fillna(0, inplace=True)

    # Change date to make sure it is correct type
    df_dates['ymd'] = pd.to_datetime(df_dates['ymd'])
    return df_dates

def transact_data(df, category):
    # Create the sets of data
    dff = df[df['category'].isin(make_list(category))].groupby(['ymd','category']).agg({'amount':'sum'}).reset_index()
    data = []
    for category in np.sort(dff['category'].unique()):
      dff_tmp = dff[dff['category']==category]
      data.append(
          go.Bar(x=dff_tmp.ymd, y=-dff_tmp['amount'], name = category)
      )
    return {
        'data': data,
        'layout': go.Layout(
            xaxis={
                'title': 'Date',
            },
            yaxis={
                'title': 'Cost'
            },
            margin={'l': 40, 'b': 40, 't': 10, 'r': 0},
            hovermode='closest',
            barmode='group'
        )
    }

def avg_spend(df_dates, category):
    # Create the sets of data
    tmp = df_dates[df_dates['category'].isin(make_list(category))]
    tmp = tmp.groupby(['ymd','category']).agg({'amount':'sum'})
    tmp = tmp.reset_index()
    avg = tmp.groupby(['category'])['amount'].rolling(window=30).sum().rolling(window=5).mean()
    tmp['rolling_avg'] = avg.reset_index(0, drop=True)
    data = []

    # Create graphs
    for category in np.sort(tmp['category'].unique()):
      plt_tmp = tmp[tmp['category']==category]
      data.append(
          go.Scatter(
            x=plt_tmp.ymd,
            y=-plt_tmp['rolling_avg'],
            name = category
            )
      )
    # Update figure object features
    return {
        'data': data,
        'layout': go.Layout(
            xaxis={
                'title': 'Date',
            },
            yaxis={
                'title': 'Average Monthly Spend'
            },
            margin={'l': 40, 'b': 40, 't': 10, 'r': 0},
            hovermode='closest',
            barmode='group'
        )
    }

# Plot cumulative wealth
# Function for plotting wealth over time
def cum_wealth(df, start_date, end_date):
  '''
  Calculate cumulative change in wealth between a
  start and end date.

  Parameters:
    df (Pandas.DataFrame): DataFrame containing monzo transactions
    start_date (string): the start date for calculating wealth change
    end_date (string): the end date for calculating wealth change

  Returns:
    plot

  '''
  # Filter by start and end date:
  df_tmp = df.loc[
      (df.ymd > dt.datetime.strptime(start_date, "%Y-%m-%d").date()) &
      (df.ymd < dt.datetime.strptime(end_date, "%Y-%m-%d").date())
  ]

  # Exclude all transfers
  df_tmp = df_tmp[df_tmp.category != 'transfer']

  # Sort by date
  df_tmp = df_tmp.sort_values(by=['ymd'])


  # Create a DataFrame of net savings over time
  rolling_amount = df_tmp.amount.cumsum()
  date = df_tmp.ymd
  df_plt = pd.DataFrame({"date":date,"rolling_amount":rolling_amount})
  df_plt.head()

  #Make plot
  data = [go.Scatter(x = df_plt.date, y = df_plt['rolling_amount'])]
  # Update figure object features
  return {
    'data': data,
    'layout': go.Layout(
        xaxis={
            'title': 'Date',
        },
        yaxis={
            'title': 'Wealth'
        },
        margin={'l': 40, 'b': 40, 't': 10, 'r': 0}
    )
  }

# Create expenses pie
def expense_pie(df, start_date, end_date):
  # Filter by start and end date:
  df_tmp = df.loc[
        (df.ymd > dt.datetime.strptime(start_date, "%Y-%m-%d").date()) &
        (df.ymd < dt.datetime.strptime(end_date, "%Y-%m-%d").date())
    ]

  # Exclude all transfers and salary
  df_tmp = df_tmp[~df_tmp.category.isin(['salary','transfer'])]

  # Create summary values
  df_sum = df_tmp.groupby('category').agg({'amount':'sum'}).reset_index()
  df_sum['amount'] = -df_sum.amount
  df_sum['count'] = df_tmp.groupby('category').agg({'amount':'count'}).reset_index(0, drop=True)
  df_sum.head()

  # Create plot
  labels = df_sum.category
  values = df_sum.amount

  trace = go.Pie(labels=labels, values=values, hole = .5)
  # Update figure object features
  return {
  'data': [trace],
  'layout': go.Layout(
      xaxis={
          'title': 'Date',
      },
      yaxis={
          'title': 'Wealth'
      },
      margin={'l': 40, 'b': 40, 't': 10, 'r': 0}
  )
}

# Create income vs Expenses
def income_expense(df, start_date, end_date):
  # Filter by start and end date:
  df_tmp = df.loc[
        (df.ymd > dt.datetime.strptime(start_date, "%Y-%m-%d").date()) &
        (df.ymd < dt.datetime.strptime(end_date, "%Y-%m-%d").date())
    ]

  # Exclude all transfers
  df_tmp = df_tmp[~df_tmp.category.isin(['transfer'])]

  # Create new categories for income / expenditure
  df_tmp['category_income'] = np.where(df_tmp['amount']>=0, 'income', 'expenses')

  # Make all amounts > 0
  df_tmp['amount'] = np.where(df_tmp['amount']<0, -df_tmp.amount, df_tmp.amount)

  # Create summary values
  df_sum = df_tmp.groupby('category_income').agg({'amount':'sum'}).reset_index()

  # Create plot
  labels = df_sum.category_income
  values = df_sum.amount

  data = [go.Bar(
            x=labels,
            y=values,
            marker=dict(
              color=['#db4437', '#0f9d58']
            )
  )]
  # Update figure object features
  return {
  'data': data,
  'layout': go.Layout(
      xaxis={
          'title': 'Date',
      },
      yaxis={
          'title': 'Wealth'
      },
      margin={'l': 40, 'b': 40, 't': 10, 'r': 0}
  )
}
