import dash
from dash import html, dcc, Input, Output
import json
import pandas as pd
import plotly.graph_objects as go

'''
Part 1 - Import and process data into dataframes for:
 *choropleth (color-coded map) of participation ratios for each race
 *bar chart comparing each race's share of total students and AP test takers
'''
# List race groups and build the names of columns for the spreadsheet data
groups = ['Native American', 'Asian', 'Hispanic', 'Black', 'White', 'Pacific Islander', 'Multiracial']
names=['Total']
for group in groups:
    names.append(group + ' Number')
    names.append(group + ' Percent')

# Import enrollment data from US Dept Ed data portal
enrollment = pd.read_excel(
    'enrollment-overall.xlsx',
    sheet_name='Overall Enrollment',
    header=None,
    names=['State'] + names,
    index_col=0,
    usecols='B:C,E:R',
    skiprows=6,
    nrows=52
)

# Import Advanced Placement test participation data from US Dept Ed data portal
ap = pd.read_excel(
    'advanced-placement-participation-by-state-took-exam.xlsx',
    sheet_name='Total',
    header=None,
    names=['State'] + [(name + ' AP') for name in names],
    index_col=0,
    usecols='B:Q',
    skiprows=6,
    nrows=52
)


# Create dataframe for choropleth comparing the participation ratios
# Join dataframes side-by-side
df_ratios = pd.concat([enrollment, ap], axis=1)

# Calculate the participation ratio for each race
for group in groups:
    group_ratio = group + ' Participation Ratio'
    group_per_ap = group + ' Percent AP'
    group_per = group + ' Percent'
    df_ratios[group_ratio] = df_ratios[group_per_ap] / df_ratios[group_per]

# Move state names from index to a column to facilitate building the choropleth
df_ratios.reset_index(inplace=True)

# Export the data for additional analyses outside the app
df_ratios.to_csv('Supplemental/participation_ratios.csv')


# Create dataframe for bar charts
# Copy ap and move the 'AP' label from columns to rows
ap1 = ap.copy()
ap1.columns = names
ap1.index = [(index + ' AP') for index in list(ap1.index)]

# Stack enrollment & ap1 vertically and drop percent columns
df_bar = pd.concat([enrollment, ap1], axis=0)
df_bar.drop(
    columns=[(group + ' Percent') for group in groups],
    inplace=True
)

# Drop 'Number' from column names now that percents are removed
df_bar.columns = [column.replace(' Number', '') for column in list(df_bar.columns)]

#Transpose dataframe to facilitate building the bar chart
df_bar = df_bar.transpose().reset_index()
df_bar.rename(columns={'index': 'Race'}, inplace=True)


'''
Part 2 - Create Plotly Dash app
'''
# Load geojson file of US States and DC for choropleth
file = open('usStatesGeo.json')
geojson = json.load(file)

dash_app = dash.Dash(__name__, suppress_callback_exceptions=True)
app = dash_app.server

dash_app.layout = html.Div(children=[
    # First section has heading, race radio items, choropleth, and explanatory examples
    html.H1(
        children='Advanced Placement Test Participation by State and Race',
        style={'textAlign': 'center'}   
    ),
    html.Div(children=[
        html.H2(children='Race'),
        dcc.RadioItems(
            groups,
            id='race-radio',
            value='Native American',
            style={'marginTop': 25},
            labelStyle={'marginLeft': 10}
        )
    ], style={'display': 'flex'}),
    dcc.Graph(id='choropleth'),
    html.P(
        '''
        On the map, blue shading indicates that students of the selected race participate
        in AP tests at a higher rate than expected.
        Red shading indicates that they participate at a lower rate,
        and white shading is neutral.
        '''
    ),
    html.P([
        html.U('Example 1:'),
        '''
        If 50% of the students in a state are white and 50% of the students taking
        one or more AP tests are white, the participation ratio is 50% ÷ 50% = 1. 
        This would be shaded in white.
        '''
    ]),
    html.P([
        html.U('Example 2:'),
        '''
        If 24% of the students in a state are Hispanic but only 12% of the students
        taking one or more AP tests are Hispanic, the participation ratio is
        12% ÷ 24% = 0.5.
        This would be shaded in red.
        '''
    ]),
    
    # Second section has heading, state drop down, and the bar chart
    html.H1(
        children='Share of Total Enrollment and AP Test Takers by Race',
        style={'textAlign': 'center', 'marginTop': 70}
    ),
    html.Div(children=[
        html.H2(children='State:'),
        dcc.Dropdown(
            df_ratios['State'].unique(),
            id='state-dropdown',
            value='United States',
            style={'width': 200, 'marginTop': 7, 'marginLeft': 5, 'searchable': True}
        )
    ], style={'display': 'flex'}),
    dcc.Graph(id='bar-chart'),
    html.P(
        '''
        In the bar chart, a longer bar for Total Enrollment (blue) indicates 
        that a racial group is underrepresented among Advanced Placement test takers.
        A longer bar for AP Test Participation (red) indicates
        that a racial group is overrepresented among Advanced Placement test takers.
        Hovering over a bar displays the number of students in a given category.
        '''
    ),
    html.P([
        html.U('Example 3:'),
        '''
        We can see that in the United States, white students comprise over 50% of AP test takers.
        Hovering over this bar shows that 1,154,805 test takers are white.
        However, white students comprise slightly less than 50% of all students in the United States (24,669,418 students).
        '''
    ]),
    
    # Finally, link to data source
    html.Div([
        'All data is from school year 2015-16. It is available on the US Department of Education data portal:',
        html.A(
            'AP Test participation data',
            href='https://data.ed.gov/dataset/2015-16-advanced-placement-exam-taking-estimations',
            target='_blank',
            style={'marginLeft': 20}
        ),
        html.A(
            'Enrollment data',
            href='https://data.ed.gov/dataset/2015-16-estimations-for-enrollment',
            target='_blank',
            style={'marginLeft': 20}
        )
    ], style={'fontSize': 12})
], style={'fontFamily': 'Arial', 'margin': 25})

# Update the bar chart
@dash_app.callback(
    Output('bar-chart', 'figure'),
    Input('state-dropdown', 'value')
)
def get_bar(selected_state):  
    # Don't include the 'Total' row of the chart in the bar graph
    df_bar_no_total = df_bar[df_bar['Race']!='Total']
    
    fig = go.Figure()
    # Add bars showing each race's share of total state enrollment
    fig.add_trace(go.Bar(
        y=df_bar_no_total['Race'],
        x=100 * df_bar_no_total[selected_state] / df_bar.loc[0, selected_state],
        orientation='h',
        name='Total Enrollment',
        hovertemplate='Total Enrollment: %{text:,}<extra></extra>',
        text=df_bar[selected_state],
        textposition='none'
    ))
    # Add bars showing each race's share of AP test takers
    fig.add_trace(go.Bar(
        y=df_bar_no_total['Race'],
        x=100 * df_bar_no_total[(selected_state + ' AP')] / df_bar.loc[0, (selected_state + ' AP')],
        orientation='h',
        name='AP Test Participation',
        hovertemplate='AP Test Participation: %{text:,}<extra></extra>',
        text=df_bar[(selected_state + ' AP')],
        textposition='none'
    ))
    fig.update_layout(
        xaxis_title='Percentage',
        barmode='group'
    )
    return fig

# Update the choropleth
@dash_app.callback(
    Output('choropleth', 'figure'),
    Input('race-radio', 'value')
)
def get_choropleth(selected_race):
    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        geojson=geojson,
        featureidkey='properties.NAME',
        locations=df_ratios['State'],
        z=df_ratios[(selected_race + ' Participation Ratio')],
        zmin=0,
        zmax=2,
        colorscale='RdBu',
        colorbar=dict(
            title=(selected_race + ' Participation Ratio'),
            tickvals=[0, 0.5, 1, 1.5, 2],
            ticktext=['0', '0.5', '1', '1.5', '≥2']
        ),
        hovertemplate='%{text}<br>' + selected_race +
            ' Participation Ratio: %{z:.2f}<extra></extra>',
        text=df_ratios['State']
    ))
    fig.update_layout(
        geo_scope='usa'
    )
    return fig

if __name__ == '__main__':
    dash_app.run_server()