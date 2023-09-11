from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import mysql.connector as connection
import pandas as pd
import plotly.graph_objects as go

def fetch_data(query, conn):
    """Fetch data from MySQL database."""
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Database credentials
host = "localhost"
user = "root"
password = input(f'insert Password MSQL: ')
database = "classicmodels"

try:
    # Create a MySQL connection
    conn = connection.connect(host=host, user=user, password=password, database=database)

    # Include your SQL queries here
    total_revenue_query = """
    SELECT offices.city, SUM(quantityOrdered * priceEach) AS TotalRevenue
    FROM orders
    JOIN orderdetails ON orders.orderNumber = orderdetails.orderNumber
    JOIN products ON orderdetails.productCode = products.productCode
    JOIN customers ON orders.customerNumber = customers.customerNumber
    JOIN employees ON customers.salesRepEmployeeNumber = employees.employeeNumber
    JOIN offices ON employees.officeCode = offices.officeCode
    WHERE orders.status IN ('Shipped', 'Resolved')
    GROUP BY offices.city;
    """

    total_unearned_revenue_query = """
    SELECT offices.city, SUM(quantityOrdered * priceEach) AS TotalUnEarnRevenue
    FROM orders
    JOIN orderdetails ON orders.orderNumber = orderdetails.orderNumber
    JOIN products ON orderdetails.productCode = products.productCode
    JOIN customers ON orders.customerNumber = customers.customerNumber
    JOIN employees ON customers.salesRepEmployeeNumber = employees.employeeNumber
    JOIN offices ON employees.officeCode = offices.officeCode
    WHERE orders.status NOT IN ('Shipped', 'Resolved')
    GROUP BY offices.city;
    """
    
    # Fetch the data and store it in DataFrames
    total_revenue_df = fetch_data(total_revenue_query, conn)
    total_unearned_revenue_df = fetch_data(total_unearned_revenue_query, conn)

    # Close the database connection
    conn.close()

    # Merge the dataframes and calculate percentages
    df = pd.merge(total_revenue_df, total_unearned_revenue_df, on='city', how='outer')
    df['UnEarnedPercentage'] = (df['TotalUnEarnRevenue'] / (df['TotalRevenue'] + df['TotalUnEarnRevenue'])) * 100

    # Fill NaN values in 'UnEarnedPercentage' with 0
    df['UnEarnedPercentage'].fillna(0, inplace=True)

except connection.Error as e:
    print(f"An error occurred: {e}")
    exit()

# Create a Dash app
app = Dash(__name__)


app.layout = html.Div([
    dcc.Dropdown(
        id='dpdn2',
        value=['NYC', 'Boston'],
        multi=True,
        options=[{'label': x, 'value': x} for x in df.city.unique()]
    ),
    
    dcc.Graph(id='revenue-bar-graph'),
    dcc.Graph(id='revenue-percent-stack-graph'),
    dcc.Graph(id='bubble-map')
])

@app.callback(
    Output('revenue-bar-graph', 'figure'),
    Input('revenue-bar-graph', 'hoverData')
)
def update_bar_graph(_):
    return px.bar(df, x='city', y=['TotalRevenue', 'TotalUnEarnRevenue'], title='Total Revenue and Unearned Revenue by City')

@app.callback(
    Output('revenue-percent-stack-graph', 'figure'),
    Input('revenue-bar-graph', 'hoverData')
)
def update_percent_stack_graph(_):
    return px.bar(df, x='city', y='UnEarnedPercentage', title='Unearned Revenue Percentage by City', color = 'UnEarnedPercentage')

@app.callback(
    Output('bubble-map', 'figure'),
    Input('revenue-bar-graph', 'hoverData')
)
def update_bubble_map(_):
    fig = go.Figure()

    # Dummy mapping from city to longitude and latitude; replace with your actual data
    city_to_lon_lat = {
        'Boston': [-71.0589, 42.3601],
        'London': [-0.1278, 51.5074],
        'NYC': [-74.0060, 40.7128],
        'Paris': [2.3522, 48.8566],
        'Tokyo': [139.6917, 35.6895],
        'Sydney': [151.2093, -33.8688]
    }

    df['lon'] = df['city'].map(lambda x: city_to_lon_lat.get(x, [None])[0])
    df['lat'] = df['city'].map(lambda x: city_to_lon_lat.get(x, [None, None])[1])

    color_scale = ['RdYlBu'] * len(df)
    df['TotalUnEarnRevenue'].fillna(0, inplace=True)

# Create the Scattergeo plot with cleaned data
    fig.add_trace(go.Scattergeo(
    lon=df['lon'],
    lat=df['lat'],
    text=df['city'],
    mode='markers',
    marker=dict(
        size=df['TotalUnEarnRevenue']/1000,
        colorscale='RdYlBu',
        showscale=True,
        opacity=0.6
        )
    ))

    fig.update_layout(
        title_text='Bubble Map',
        geo=dict(
            scope='world'
        )
    )

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
