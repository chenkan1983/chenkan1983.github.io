import pandas as pd
import networkx as nx
from dash import Dash, html, dcc
import plotly.graph_objects as go

# 读取数据
df = pd.read_csv('../data/family_members.csv')

# 创建图
G = nx.DiGraph()

# 添加节点
for _, row in df.iterrows():
    G.add_node(row['id'], 
               name=row['name'],
               birth_year=row['birth_year'],
               death_year=row['death_year'],
               generation=row['generation'],
               role=row['role'])

# 添加边
for _, row in df.iterrows():
    if row['parent_id'] != 0:
        G.add_edge(row['parent_id'], row['id'])

# 创建Dash应用
app = Dash(__name__)

# 设置布局
pos = nx.spring_layout(G)
edge_trace = go.Scatter(
    x=[], y=[],
    line=dict(width=0.5, color='#888'),
    hoverinfo='none',
    mode='lines')

for edge in G.edges():
    x0, y0 = pos[edge[0]]
    x1, y1 = pos[edge[1]]
    edge_trace['x'] += (x0, x1, None)
    edge_trace['y'] += (y0, y1, None)

node_trace = go.Scatter(
    x=[], y=[],
    text=[],
    mode='markers+text',
    hoverinfo='text',
    marker=dict(
        showscale=True,
        colorscale='YlOrRd',
        size=30,
        colorbar=dict(
            thickness=15,
            title='代际',
            xanchor='left',
            titleside='right'
        )
    )
)

for node in G.nodes():
    x, y = pos[node]
    node_trace['x'] += (x,)
    node_trace['y'] += (y,)
    node_info = G.nodes[node]
    node_trace['text'] += (f"{node_info['name']}<br>{node_info['birth_year']}-{node_info['death_year']}<br>{node_info['role']}",)
    node_trace['marker']['color'] = tuple(list(node_trace['marker']['color']) + [node_info['generation']])

# 创建图形
fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    title='洛克菲勒家族关系图',
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                )

app.layout = html.Div([
    html.H1('洛克菲勒家族关系图研究'),
    dcc.Graph(figure=fig),
    html.Div([
        html.H3('家族成员信息'),
        html.Div(id='member-info')
    ])
])

if __name__ == '__main__':
    app.run_server(debug=True, port=8050) 