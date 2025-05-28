import streamlit as st
import os
import subprocess
import networkx as nx
import plotly.graph_objects as go
import numpy as np
import json
from pathlib import Path
import time

st.set_page_config(page_title="GraphRAG Knowledge Graph Explorer", layout="wide")

# Title and description
st.title("GraphRAG Knowledge Graph Explorer")
st.markdown("""
This application allows you to interact with the GraphRAG knowledge graph.
You can ask questions about your data using either Local or Global search methods,
and visualize the knowledge graph.
""")

# Sidebar for configuration
st.sidebar.title("Configuration")
root_dir = st.sidebar.text_input("Root Directory", value="./ragtest")
community_level = st.sidebar.slider("Community Level", min_value=0, max_value=5, value=2,
                                  help="Community level in the Leiden community hierarchy. Higher value means we use reports on smaller communities.")
response_type = st.sidebar.text_input("Response Type", value="Multiple Paragraphs",
                                    help="Format of the response (e.g., Multiple Paragraphs, Single Paragraph, List of 3-7 Points)")

# Function to run graphRAG query and get the response
@st.cache_data
def run_graphrag_query(query, method="global"):
    try:
        result = subprocess.run(
            ["python", "-m", "graphrag.query", "--root", root_dir, "--method", method, 
             "--community_level", str(community_level), "--response_type", response_type, query],
            capture_output=True,
            text=True,
            check=True
        )
        # Process completed. Check if we got a meaningful response
        if not result.stdout.strip():
            return "The query completed but returned no results."
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

# Function to load the GraphML file
@st.cache_data
def find_latest_graphml():
    output_dir = Path(root_dir) / "output"
    if not output_dir.exists():
        return None
    
    # Find the most recent timestamp directory
    timestamp_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    if not timestamp_dirs:
        return None
    
    latest_dir = max(timestamp_dirs, key=lambda d: d.stat().st_mtime)
    graphml_path = latest_dir / "artifacts" / "summarized_graph.graphml"
    
    if graphml_path.exists():
        return str(graphml_path)
    
    # Look for any graphml file if the standard one isn't found
    artifacts_dir = latest_dir / "artifacts"
    if artifacts_dir.exists():
        graphml_files = list(artifacts_dir.glob("*.graphml"))
        if graphml_files:
            return str(graphml_files[0])
    
    return None

# Function to visualize the graph
@st.cache_data
def visualize_graph(graphml_path):
    if not graphml_path or not os.path.exists(graphml_path):
        return None
    
    graph = nx.read_graphml(graphml_path)
    
    # Create a 3D spring layout
    pos = nx.spring_layout(graph, dim=3, seed=42, k=0.5)
    
    # Extract node positions
    x_nodes = [pos[node][0] for node in graph.nodes()]
    y_nodes = [pos[node][1] for node in graph.nodes()]
    z_nodes = [pos[node][2] for node in graph.nodes()]
    
    # Extract edge positions
    x_edges = []
    y_edges = []
    z_edges = []
    
    for edge in graph.edges():
        x_edges.extend([pos[edge[0]][0], pos[edge[1]][0], None])
        y_edges.extend([pos[edge[0]][1], pos[edge[1]][1], None])
        z_edges.extend([pos[edge[0]][2], pos[edge[1]][2], None])
    
    # Generate node colors based on communities or degree
    if 'community' in next(iter(graph.nodes(data=True)))[1]:
        # Use community for coloring
        communities = list(set(data['community'] for _, data in graph.nodes(data=True) if 'community' in data))
        community_to_int = {c: i for i, c in enumerate(communities)}
        node_colors = [community_to_int.get(graph.nodes[node].get('community', 0), 0) 
                       for node in graph.nodes()]
        colorbar_title = 'Community'
    else:
        # Use degree for coloring
        node_colors = [graph.degree(node) for node in graph.nodes()]
        colorbar_title = 'Node Degree'
    
    # Normalize colors
    node_colors = np.array(node_colors)
    if node_colors.size > 0 and node_colors.max() != node_colors.min():
        node_colors = (node_colors - node_colors.min()) / (node_colors.max() - node_colors.min())
    
    # Get node sizes based on degree
    node_sizes = [5 + 3 * graph.degree(node) for node in graph.nodes()]
    
    # Create the trace for edges
    edge_trace = go.Scatter3d(
        x=x_edges, y=y_edges, z=z_edges,
        mode='lines',
        line=dict(color='lightgray', width=0.5),
        hoverinfo='none'
    )
    
    # Create the trace for nodes
    node_trace = go.Scatter3d(
        x=x_nodes, y=y_nodes, z=z_nodes,
        mode='markers',
        marker=dict(
            size=node_sizes,
            color=node_colors,
            colorscale='Viridis',
            colorbar=dict(
                title=colorbar_title,
                thickness=10,
                x=1.1
            ),
            line=dict(width=1)
        ),
        text=[f"Node: {node}<br>Type: {graph.nodes[node].get('type', 'N/A')}<br>Description: {graph.nodes[node].get('description', 'N/A')}" 
              for node in graph.nodes()],
        hoverinfo='text'
    )
    
    # Create the 3D plot
    fig = go.Figure(data=[edge_trace, node_trace])
    
    # Update layout for better visualization
    fig.update_layout(
        title='Knowledge Graph Visualization',
        showlegend=False,
        scene=dict(
            xaxis=dict(showbackground=False),
            yaxis=dict(showbackground=False),
            zaxis=dict(showbackground=False)
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        height=700
    )
    
    return fig

# Create tabs for different functionalities
query_tab, visualize_tab = st.tabs(["Query Knowledge Graph", "Visualize Knowledge Graph"])

with query_tab:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("Ask a question")
        query = st.text_area("Enter your query")
        
    with col2:
        st.header("Search Method")
        search_method = st.radio(
            "Select search method",
            ["global", "local"],
            help="Global search is good for holistic questions about the corpus. Local search is better for specific entity questions."
        )
    
    if st.button("Submit Query"):
        if query:
            with st.spinner(f"Running {search_method} search..."):
                response = run_graphrag_query(query, method=search_method)
                st.subheader("Response:")
                st.write(response)
        else:
            st.warning("Please enter a query to search.")

with visualize_tab:
    st.header("Knowledge Graph Visualization")
    
    # Button to refresh graph
    if st.button("Load/Refresh Graph"):
        with st.spinner("Loading graph..."):
            graphml_path = find_latest_graphml()
            if graphml_path:
                st.session_state['graphml_path'] = graphml_path
                st.success(f"Loaded graph from: {graphml_path}")
            else:
                st.error("No GraphML file found. Make sure you've run the indexing process with snapshots.graphml: yes in settings.yaml")
    
    # Display the graph if available
    if 'graphml_path' in st.session_state:
        with st.spinner("Generating visualization..."):
            fig = visualize_graph(st.session_state['graphml_path'])
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                # Display graph statistics
                graph = nx.read_graphml(st.session_state['graphml_path'])
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Nodes", len(graph.nodes))
                with col2:
                    st.metric("Edges", len(graph.edges))
                with col3:
                    if nx.is_connected(graph):
                        st.metric("Connected Components", 1)
                    else:
                        st.metric("Connected Components", nx.number_connected_components(graph))
                
                # Export options
                if st.download_button("Download Graph as GraphML", 
                                    data=open(st.session_state['graphml_path'], 'rb').read(),
                                    file_name="knowledge_graph.graphml"):
                    st.success("Download started!")
            else:
                st.error("Failed to visualize the graph.")
    else:
        st.info("Click 'Load/Refresh Graph' to load and visualize the knowledge graph.")

# Footer
st.markdown("---")
st.caption("GraphRAG Knowledge Graph Explorer - Built with Streamlit")
