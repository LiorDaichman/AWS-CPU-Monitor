import os
from flask import Flask, request, render_template
import dash
from dash import dcc, html
import boto3
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

server = Flask(__name__)
app = dash.Dash(__name__, server=server, routes_pathname_prefix="/dash/")

def get_cpu_usage(instance_id, start_time, end_time, period):
    client = boto3.client('cloudwatch',aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY,region_name=AWS_REGION)
    response = client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=period,
        Statistics=['Average']
    )
    data_points = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
    times = [point['Timestamp'] for point in data_points]
    values = [point['Average'] for point in data_points]
    return times, values

def get_instance_id_by_ip(ip_address):
    ec2 = boto3.client('ec2',aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY,region_name=AWS_REGION)
    response = ec2.describe_instances(Filters=[
        {'Name': 'private-ip-address', 'Values': [ip_address]} ])
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            return instance['InstanceId']
    return None

app.layout = html.Div([
    html.H1("AWS Instance CPU Usage", style={'margin-bottom': '20px'}),
    html.Div([
    html.Label("Time Period (Hours): ", style={'display': 'block', 'font-weight': 'bold'}),
    dcc.Input(id='time-period',type='number', value=24, min=1, style={'width': '200px'})
    ], style={'margin-bottom': '10px'}),
    html.Div([
        html.Label("Period (Seconds): ", style={'display': 'block', 'font-weight': 'bold'}),
        dcc.Input(id='period', type='number', value=3600, style={'width': '200px'})
    ], style={'margin-bottom': '10px'}),
    html.Div([
        html.Label("IP Address: ", style={'display': 'block', 'font-weight': 'bold'}),
        dcc.Input(id='instance-id', type='text', value="Enter IP Address", style={'width': '200px'})
    ], style={'margin-bottom': '10px'}),
    html.Div([
        html.Button('Load', id='load-button', n_clicks=0)
    ], style={'margin-bottom': '20px'}),
    dcc.Graph(id='cpu-usage-graph')
])

@app.callback(
    dash.Output('cpu-usage-graph', 'figure'),
    [
        dash.Input('load-button', 'n_clicks')
    ],
    [
        dash.State('time-period', 'value'),
        dash.State('period', 'value'),
        dash.State('instance-id', 'value')
    ]
)

def update_graph(n_clicks, time_period, period, ip_address):
    if n_clicks > 0:
        instance_id = get_instance_id_by_ip(ip_address)
        if not instance_id:
            return {'data': [], 'layout': {'title': 'Error: Invalid IP Address or Instance Not Found'}}
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=int(time_period))
        time_range_seconds = int(time_period) * 3600
        min_period = max(60, (time_range_seconds // 1440)) 
        period = max(min_period, ((int(period) // 60) * 60)) 
        if period != int(period):
            print(f"Adjusted period to {period} seconds (must be multiple of 60).")
        times, values = get_cpu_usage(instance_id, start_time, end_time, int(period))
        figure = {
            'data': [{'x': times, 'y': values, 'type': 'line', 'name': 'CPU Usage'}],
            'layout': {'xaxis': {'title': 'Time'},'yaxis': {'title': 'CPU Utilization (%)'}}                                              
        }
        return figure
    return {'data': [], 'layout': {}}

@server.route("/")
def home():
    return render_template()

if __name__ == "__main__":
    app.run(debug=True)
