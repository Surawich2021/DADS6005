from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import mysql.connector as connection
import pandas as pd
import plotly.graph_objects as go

def fetch_data(query, conn):
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"Failed query: {query}")
        return None

# Database credentials
host = "localhost"
user = "root"
password = '1234SQL'
database = "classicmodels"

try:
    conn = connection.connect(host=host, user=user, password=password, database=database)

    # Your SQL queries here
    line_chart_query = """
    SELECT orders.orderDate, products.productline, SUM(quantityOrdered * priceEach) AS TotalRevenue
    FROM orders
    JOIN orderdetails ON orders.orderNumber = orderdetails.orderNumber
    JOIN products ON orderdetails.productCode = products.productCode
    WHERE orders.status IN ('Shipped', 'Resolved')
    GROUP BY products.productline, orders.orderDate
    ORDER BY orders.orderDate, products.productline;
    """

    total_revenue_query = """
    SELECT products.productline, SUM(quantityOrdered * priceEach) AS TotalRevenue
    FROM orders
    JOIN orderdetails ON orders.orderNumber = orderdetails.orderNumber
    JOIN products ON orderdetails.productCode = products.productCode
    WHERE orders.status IN ('Shipped', 'Resolved')
    GROUP BY products.productline;
    """

    total_unearned_revenue_query = """
    SELECT products.productline, SUM(quantityOrdered * priceEach) AS TotalUnEarnRevenue
    FROM orders
    JOIN orderdetails ON orders.orderNumber = orderdetails.orderNumber
    JOIN products ON orderdetails.productCode = products.productCode
    JOIN customers ON orders.customerNumber = customers.customerNumber
    JOIN employees ON customers.salesRepEmployeeNumber = employees.employeeNumber
    JOIN offices ON employees.officeCode = offices.officeCode
    WHERE orders.status NOT IN ('Shipped', 'Resolved')
    GROUP BY products.productline;
    """
    
    total_revenue_df = fetch_data(total_revenue_query, conn)
    total_unearned_revenue_df = fetch_data(total_unearned_revenue_query, conn)
    df_line = fetch_data(line_chart_query, conn)
    
    if total_revenue_df is None or total_unearned_revenue_df is None:
        print("One of the dataframes is None, exiting.")
        exit()

    conn.close()
    
    df = pd.merge(total_revenue_df, total_unearned_revenue_df, on='productline', how='outer')
    df['UnEarnedPercentage'] = (df['TotalUnEarnRevenue'] / (df['TotalRevenue'] + df['TotalUnEarnRevenue'])) * 100
    df['UnEarnedPercentage'].fillna(0, inplace=True)
    df.describe()

except connection.Error as e:
    print(f"An error occurred: {e}")
    exit()

app = Dash(__name__)
app.layout = html.Div([
    dcc.Dropdown(
        id='dpdn2',
        value=['Motorcycles', 'Classic Cars'],
        multi=True,
        options=[{'label': x, 'value': x} for x in df.productline.unique()]
    ),
    dcc.Graph(id='revenue-bar-graph'),
    dcc.Graph(id='revenue-percent-stack-graph'),
    dcc.Graph(id='line-chart')
])

# Callbacks for updating graphs
@app.callback(
    Output('revenue-bar-graph', 'figure'),
    Input('revenue-bar-graph', 'hoverData')
)
def update_bar_graph(_):
    return px.bar(df, x='productline', y=['TotalRevenue', 'TotalUnEarnRevenue'], title='Total Revenue and Unearned Revenue by Productline')

@app.callback(
    Output('revenue-percent-stack-graph', 'figure'),
    Input('revenue-bar-graph', 'hoverData')
)
def update_percent_stack_graph(_):
    return px.bar(df, x='productline', y='UnEarnedPercentage', title='Unearned Revenue Percentage by Productline', color='UnEarnedPercentage')

@app.callback(
    Output('line-chart', 'figure'),
    [Input('dpdn2', 'value')]
)
def update_line_chart(selected_productlines):
    print(f"Selected product lines: {selected_productlines}")  # Debug print
    filtered_df = df_line[df_line['productline'].isin(selected_productlines)]
    print(f"Filtered DataFrame:\n{filtered_df.head()}")  # Debug print

    if filtered_df.empty:
        return go.Figure()  # Return an empty figure if the DataFrame is empty

    fig = px.line(
        filtered_df, 
        x='orderDate', 
        y='TotalRevenue', 
        color='productline', 
        title='Revenue Over Time by Product Line'
    )
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
