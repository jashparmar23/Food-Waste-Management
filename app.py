import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Database connection
@st.cache_resource
def init_connection():
    return sqlite3.connect('food_management.db', check_same_thread=False)

conn = init_connection()

# Page config
st.set_page_config(
    page_title="Food Wastage Management System",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #2E8B57;
    }
    .success-message {
        color: #008000;
        font-weight: bold;
    }
    .error-message {
        color: #FF0000;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# The 15 SQL Queries
queries = [
    """
    SELECT 
        p.City,
        COUNT(DISTINCT p.Provider_ID) as Total_Providers,
        COUNT(DISTINCT r.Receiver_ID) as Total_Receivers
    FROM providers p
    LEFT JOIN receivers r ON p.City = r.City
    GROUP BY p.City
    ORDER BY Total_Providers DESC;
    """,
    
    """
    SELECT 
        p.Type as Provider_Type,
        COUNT(fl.Food_ID) as Total_Food_Listings,
        SUM(fl.Quantity) as Total_Quantity
    FROM providers p
    JOIN food_listings fl ON p.Provider_ID = fl.Provider_ID
    GROUP BY p.Type
    ORDER BY Total_Quantity DESC;
    """,
    
    """
    SELECT 
        City,
        Name,
        Type,
        Contact,
        Address
    FROM providers
    ORDER BY City, Name;
    """,
    
    """
    SELECT 
        r.Name as Receiver_Name,
        r.Type as Receiver_Type,
        r.City,
        COUNT(c.Claim_ID) as Total_Claims,
        SUM(fl.Quantity) as Total_Quantity_Claimed
    FROM receivers r
    JOIN claims c ON r.Receiver_ID = c.Receiver_ID
    JOIN food_listings fl ON c.Food_ID = fl.Food_ID
    WHERE c.Status = 'Completed'
    GROUP BY r.Receiver_ID, r.Name, r.Type, r.City
    ORDER BY Total_Quantity_Claimed DESC
    LIMIT 10;
    """,
    
    """
    SELECT 
        SUM(Quantity) as Total_Available_Quantity,
        COUNT(Food_ID) as Total_Food_Items,
        COUNT(DISTINCT Provider_ID) as Total_Active_Providers
    FROM food_listings;
    """,
    
    """
    SELECT 
        Location as City,
        COUNT(Food_ID) as Total_Listings,
        SUM(Quantity) as Total_Quantity,
        AVG(Quantity) as Average_Quantity_Per_Listing
    FROM food_listings
    GROUP BY Location
    ORDER BY Total_Listings DESC;
    """,
    
    """
    SELECT 
        Food_Type,
        COUNT(Food_ID) as Total_Listings,
        SUM(Quantity) as Total_Quantity,
        ROUND(AVG(Quantity), 2) as Average_Quantity
    FROM food_listings
    GROUP BY Food_Type
    ORDER BY Total_Quantity DESC;
    """,
    
    """
    SELECT 
        fl.Food_Name,
        fl.Food_Type,
        fl.Meal_Type,
        COUNT(c.Claim_ID) as Total_Claims,
        fl.Quantity as Available_Quantity
    FROM food_listings fl
    LEFT JOIN claims c ON fl.Food_ID = c.Food_ID
    GROUP BY fl.Food_ID, fl.Food_Name, fl.Food_Type, fl.Meal_Type, fl.Quantity
    ORDER BY Total_Claims DESC
    LIMIT 15;
    """,
    
    """
    SELECT 
        p.Name as Provider_Name,
        p.Type as Provider_Type,
        p.City,
        COUNT(c.Claim_ID) as Successful_Claims,
        SUM(fl.Quantity) as Total_Quantity_Claimed
    FROM providers p
    JOIN food_listings fl ON p.Provider_ID = fl.Provider_ID
    JOIN claims c ON fl.Food_ID = c.Food_ID
    WHERE c.Status = 'Completed'
    GROUP BY p.Provider_ID, p.Name, p.Type, p.City
    ORDER BY Successful_Claims DESC
    LIMIT 10;
    """,
    
    """
    SELECT 
        Status,
        COUNT(*) as Count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM claims), 2) as Percentage
    FROM claims
    GROUP BY Status
    ORDER BY Count DESC;
    """,
    
    """
    SELECT 
        r.Type as Receiver_Type,
        COUNT(DISTINCT r.Receiver_ID) as Total_Receivers,
        SUM(fl.Quantity) as Total_Quantity_Claimed,
        ROUND(AVG(fl.Quantity), 2) as Average_Quantity_Per_Claim
    FROM receivers r
    JOIN claims c ON r.Receiver_ID = c.Receiver_ID
    JOIN food_listings fl ON c.Food_ID = fl.Food_ID
    WHERE c.Status = 'Completed'
    GROUP BY r.Type
    ORDER BY Average_Quantity_Per_Claim DESC;
    """,
    
    """
    SELECT 
        fl.Meal_Type,
        COUNT(c.Claim_ID) as Total_Claims,
        SUM(fl.Quantity) as Total_Quantity_Claimed,
        ROUND(AVG(fl.Quantity), 2) as Average_Quantity_Per_Claim
    FROM food_listings fl
    JOIN claims c ON fl.Food_ID = c.Food_ID
    WHERE c.Status = 'Completed'
    GROUP BY fl.Meal_Type
    ORDER BY Total_Quantity_Claimed DESC;
    """,
    
    """
    SELECT 
        p.Name as Provider_Name,
        p.Type as Provider_Type,
        p.City,
        COUNT(fl.Food_ID) as Total_Food_Items,
        SUM(fl.Quantity) as Total_Quantity_Donated
    FROM providers p
    LEFT JOIN food_listings fl ON p.Provider_ID = fl.Provider_ID
    GROUP BY p.Provider_ID, p.Name, p.Type, p.City
    ORDER BY Total_Quantity_Donated DESC
    LIMIT 15;
    """,
    
    """
    SELECT 
        fl.Food_Name,
        fl.Food_Type,
        fl.Meal_Type,
        fl.Quantity,
        fl.Expiry_Date,
        fl.Location,
        p.Name as Provider_Name,
        p.Contact as Provider_Contact,
        julianday(fl.Expiry_Date) - julianday('now') as Days_Until_Expiry
    FROM food_listings fl
    JOIN providers p ON fl.Provider_ID = p.Provider_ID
    WHERE julianday(fl.Expiry_Date) - julianday('now') <= 7 
        AND julianday(fl.Expiry_Date) - julianday('now') >= 0
    ORDER BY Days_Until_Expiry ASC;
    """,
    
    """
    SELECT 
        strftime('%Y-%m', c.Timestamp) as Month,
        COUNT(c.Claim_ID) as Total_Claims,
        COUNT(CASE WHEN c.Status = 'Completed' THEN 1 END) as Completed_Claims,
        COUNT(CASE WHEN c.Status = 'Pending' THEN 1 END) as Pending_Claims,
        COUNT(CASE WHEN c.Status = 'Cancelled' THEN 1 END) as Cancelled_Claims
    FROM claims c
    GROUP BY strftime('%Y-%m', c.Timestamp)
    ORDER BY Month DESC;
    """
]

# Query descriptions
query_descriptions = [
    "1. Food Providers and Receivers Count by City",
    "2. Provider Type Contribution Analysis", 
    "3. Provider Contact Information by City",
    "4. Top 10 Receivers by Quantity Claimed",
    "5. Overall Food Availability Statistics",
    "6. Food Listings Count by City",
    "7. Food Type Availability Analysis",
    "8. Top 15 Food Items by Number of Claims",
    "9. Top 10 Providers by Successful Claims",
    "10. Claims Status Distribution",
    "11. Average Quantity Claimed by Receiver Type",
    "12. Meal Type Claims Analysis",
    "13. Top 15 Providers by Total Quantity Donated",
    "14. Food Items Expiring Within 7 Days",
    "15. Monthly Claims Trend"
]

# CRUD Functions
def insert_provider(provider_id, name, type_, address, city, contact):
    cursor = conn.cursor()
    sql = '''INSERT INTO providers (Provider_ID, Name, Type, Address, City, Contact) VALUES (?, ?, ?, ?, ?, ?)'''
    cursor.execute(sql, (provider_id, name, type_, address, city, contact))
    conn.commit()
    return f"Provider {name} inserted successfully."

def insert_receiver(receiver_id, name, type_, city, contact):
    cursor = conn.cursor()
    sql = '''INSERT INTO receivers (Receiver_ID, Name, Type, City, Contact) VALUES (?, ?, ?, ?, ?)'''
    cursor.execute(sql, (receiver_id, name, type_, city, contact))
    conn.commit()
    return f"Receiver {name} inserted successfully."

def insert_food_listing(food_id, food_name, quantity, expiry_date, provider_id, provider_type, location, food_type, meal_type):
    cursor = conn.cursor()
    sql = '''INSERT INTO food_listings (Food_ID, Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    cursor.execute(sql, (food_id, food_name, quantity, expiry_date, provider_id, provider_type, location, food_type, meal_type))
    conn.commit()
    return f"Food listing {food_name} inserted successfully."

def insert_claim(claim_id, food_id, receiver_id, status, timestamp):
    cursor = conn.cursor()
    sql = '''INSERT INTO claims (Claim_ID, Food_ID, Receiver_ID, Status, Timestamp) VALUES (?, ?, ?, ?, ?)'''
    cursor.execute(sql, (claim_id, food_id, receiver_id, status, timestamp))
    conn.commit()
    return f"Claim {claim_id} inserted successfully."

def update_provider_contact(provider_id, new_contact):
    cursor = conn.cursor()
    sql = '''UPDATE providers SET Contact = ? WHERE Provider_ID = ?'''
    cursor.execute(sql, (new_contact, provider_id))
    conn.commit()
    return f"Provider {provider_id} contact updated to {new_contact}."

def update_receiver_contact(receiver_id, new_contact):
    cursor = conn.cursor()
    sql = '''UPDATE receivers SET Contact = ? WHERE Receiver_ID = ?'''
    cursor.execute(sql, (new_contact, receiver_id))
    conn.commit()
    return f"Receiver {receiver_id} contact updated to {new_contact}."

def update_food_quantity(food_id, new_quantity):
    cursor = conn.cursor()
    sql = '''UPDATE food_listings SET Quantity = ? WHERE Food_ID = ?'''
    cursor.execute(sql, (new_quantity, food_id))
    conn.commit()
    return f"Food listing {food_id} quantity updated to {new_quantity}."

def update_claim_status(claim_id, new_status):
    cursor = conn.cursor()
    sql = '''UPDATE claims SET Status = ? WHERE Claim_ID = ?'''
    cursor.execute(sql, (new_status, claim_id))
    conn.commit()
    return f"Claim {claim_id} status updated to {new_status}."

def delete_provider(provider_id):
    cursor = conn.cursor()
    sql = '''DELETE FROM providers WHERE Provider_ID = ?'''
    cursor.execute(sql, (provider_id,))
    conn.commit()
    return f"Provider {provider_id} deleted successfully."

def delete_receiver(receiver_id):
    cursor = conn.cursor()
    sql = '''DELETE FROM receivers WHERE Receiver_ID = ?'''
    cursor.execute(sql, (receiver_id,))
    conn.commit()
    return f"Receiver {receiver_id} deleted successfully."

def delete_food_listing(food_id):
    cursor = conn.cursor()
    sql = '''DELETE FROM food_listings WHERE Food_ID = ?'''
    cursor.execute(sql, (food_id,))
    conn.commit()
    return f"Food listing {food_id} deleted successfully."

def delete_claim(claim_id):
    cursor = conn.cursor()
    sql = '''DELETE FROM claims WHERE Claim_ID = ?'''
    cursor.execute(sql, (claim_id,))
    conn.commit()
    return f"Claim {claim_id} deleted successfully."

# Function to create ALL 15 visualizations
def create_all_15_visualizations(df, query_index, description):
    """Create appropriate visualization for each of the 15 queries"""
    
    if df.empty:
        st.warning(f"⚠️ No data available for visualization: {description}")
        return None
    
    try:
        if query_index == 0:  # Query 1: Providers and receivers by city
            st.markdown("### 📊 Visualization 1")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['City'], y=df['Total_Providers'], name='Providers', marker_color='lightblue'))
            fig.add_trace(go.Bar(x=df['City'], y=df['Total_Receivers'], name='Receivers', marker_color='lightcoral'))
            fig.update_layout(title=description, barmode='group', xaxis_title='City', yaxis_title='Count')
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 1:  # Query 2: Provider type contribution
            st.markdown("### 📊 Visualization 2")
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.bar(df, x='Provider_Type', y='Total_Quantity', title='Total Quantity by Provider Type')
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.pie(df, values='Total_Food_Listings', names='Provider_Type', title='Food Listings Distribution')
                st.plotly_chart(fig2, use_container_width=True)
                
        elif query_index == 2:  # Query 3: Provider contact info
            st.markdown("### 📊 Visualization 3")
            st.info("📋 Provider contact information is best displayed in table format above")
            # Create a simple summary chart
            city_counts = df['City'].value_counts()
            fig = px.bar(x=city_counts.index, y=city_counts.values, title='Number of Providers by City')
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 3:  # Query 4: Top receivers by quantity claimed
            st.markdown("### 📊 Visualization 4")
            fig = px.bar(df, x='Total_Quantity_Claimed', y='Receiver_Name', orientation='h', 
                        title=description, color='Total_Quantity_Claimed', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 4:  # Query 5: Overall food availability
            st.markdown("### 📊 Visualization 5")
            labels = ['Total Food Items', 'Total Active Providers']
            values = [df['Total_Food_Items'].iloc[0], df['Total_Active_Providers'].iloc[0]]
            fig = px.pie(values=values, names=labels, title=description)
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 5:  # Query 6: Food listings by city
            st.markdown("### 📊 Visualization 6")
            fig = px.bar(df, x='City', y='Total_Listings', title=description, 
                        color='Total_Listings', color_continuous_scale='Greens')
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 6:  # Query 7: Food type availability
            st.markdown("### 📊 Visualization 7")
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.bar(df, x='Food_Type', y='Total_Quantity', title='Total Quantity by Food Type')
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.pie(df, values='Total_Listings', names='Food_Type', title='Food Type Distribution')
                st.plotly_chart(fig2, use_container_width=True)
                
        elif query_index == 7:  # Query 8: Claims per food item
            st.markdown("### 📊 Visualization 8")
            fig = px.bar(df.head(10), x='Total_Claims', y='Food_Name', orientation='h', 
                        title='Top 10 Food Items by Claims', color='Total_Claims', color_continuous_scale='Oranges')
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 8:  # Query 9: Top providers by successful claims
            st.markdown("### 📊 Visualization 9")
            fig = px.bar(df, x='Successful_Claims', y='Provider_Name', orientation='h', 
                        title=description, color='Successful_Claims', color_continuous_scale='Purples')
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 9:  # Query 10: Claims status distribution
            st.markdown("### 📊 Visualization 10")
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.pie(df, values='Count', names='Status', title='Claims Status Distribution')
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.bar(df, x='Status', y='Percentage', title='Claims Status Percentage')
                st.plotly_chart(fig2, use_container_width=True)
                
        elif query_index == 10:  # Query 11: Average quantity by receiver type
            st.markdown("### 📊 Visualization 11")
            fig = px.bar(df, x='Receiver_Type', y='Average_Quantity_Per_Claim', 
                        title=description, color='Average_Quantity_Per_Claim', color_continuous_scale='Reds')
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 11:  # Query 12: Meal type claims
            st.markdown("### 📊 Visualization 12")
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.bar(df, x='Meal_Type', y='Total_Claims', title='Total Claims by Meal Type')
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.bar(df, x='Meal_Type', y='Total_Quantity_Claimed', title='Total Quantity by Meal Type')
                st.plotly_chart(fig2, use_container_width=True)
                
        elif query_index == 12:  # Query 13: Food donation by provider
            st.markdown("### 📊 Visualization 13")
            fig = px.bar(df.head(10), x='Total_Quantity_Donated', y='Provider_Name', orientation='h', 
                        title='Top 10 Providers by Donation', color='Total_Quantity_Donated', color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)
            
        elif query_index == 13:  # Query 14: Food items expiring soon
            st.markdown("### 📊 Visualization 14")
            if len(df) > 0:
                fig = px.bar(df, x='Days_Until_Expiry', y='Food_Name', orientation='h', 
                            title=description, color='Days_Until_Expiry', color_continuous_scale='Reds')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ Great! No food items are expiring within 7 days.")
                
        elif query_index == 14:  # Query 15: Monthly claims trend
            st.markdown("### 📊 Visualization 15")
            if len(df) > 0:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Month'], y=df['Total_Claims'], 
                                       mode='lines+markers', name='Total Claims', line=dict(width=3)))
                fig.add_trace(go.Scatter(x=df['Month'], y=df['Completed_Claims'], 
                                       mode='lines+markers', name='Completed'))
                fig.add_trace(go.Scatter(x=df['Month'], y=df['Pending_Claims'], 
                                       mode='lines+markers', name='Pending'))
                fig.add_trace(go.Scatter(x=df['Month'], y=df['Cancelled_Claims'], 
                                       mode='lines+markers', name='Cancelled'))
                fig.update_layout(title=description, xaxis_title='Month', yaxis_title='Number of Claims')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 No monthly trend data available yet.")
                
    except Exception as e:
        st.error(f"❌ Error creating visualization: {e}")

# Function to execute and display ALL 15 query results
def display_all_15_query_results():
    st.header("📊 Complete Analysis: ALL 15 SQL Query Results & Visualizations")
    st.markdown("### 🎯 This section displays the output of all 15 SQL queries along with their corresponding visualizations")
    st.markdown("---")
    
    for i, (query, description) in enumerate(zip(queries, query_descriptions)):
        # Query header with numbering
        st.markdown(f"## **{description}**")
        
        # Expandable SQL query viewer
        with st.expander(f"🔍 View SQL Query {i+1}"):
            st.code(query, language='sql')
        
        try:
            # Execute query
            df = pd.read_sql_query(query, conn)
            
            if not df.empty:
                # Display results summary
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**📋 Query Results:** {len(df)} records returned")
                with col2:
                    st.markdown(f"**📊 Columns:** {len(df.columns)}")
                
                # Display data table
                st.dataframe(df, use_container_width=True)
                
                # Create and display visualization
                create_all_15_visualizations(df, i, description)
                
            else:
                st.warning(f"⚠️ No data available for {description}")
                
        except Exception as e:
            st.error(f"❌ Error executing Query {i+1}: {e}")
        
        # Add separator between queries
        st.markdown("---")
    
    # Summary at the end
    st.markdown("## 🎉 Analysis Complete!")
    st.success("✅ All 15 SQL queries have been executed and visualized successfully!")

# Visualization functions for analytics section
def create_provider_chart():
    try:
        query = """
        SELECT p.Type as Provider_Type, COUNT(fl.Food_ID) as Total_Food_Listings, SUM(fl.Quantity) as Total_Quantity
        FROM providers p
        JOIN food_listings fl ON p.Provider_ID = fl.Provider_ID
        GROUP BY p.Type
        ORDER BY Total_Quantity DESC;
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            fig = px.bar(df, x='Provider_Type', y='Total_Quantity', 
                         title='Food Contribution by Provider Type')
            st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("⚠️ No provider data available")

def create_claims_chart():
    try:
        query = """
        SELECT Status, COUNT(*) as Count
        FROM claims
        GROUP BY Status
        ORDER BY Count DESC;
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            fig = px.pie(df, values='Count', names='Status', 
                         title='Claims Status Distribution')
            st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("⚠️ No claims data available")

def create_food_type_chart():
    try:
        query = """
        SELECT Food_Type, COUNT(Food_ID) as Total_Listings, SUM(Quantity) as Total_Quantity
        FROM food_listings
        GROUP BY Food_Type
        ORDER BY Total_Quantity DESC;
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            fig = px.bar(df, x='Food_Type', y='Total_Quantity', 
                         title='Food Availability by Type')
            st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("⚠️ No food listings data available")

# Main Application
def main():
    st.markdown('<h1 class="main-header">🍽️ Local Food Wastage Management System</h1>', unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("📋 Navigation")
    menu = [
        "🏠 Dashboard", 
        "📊 SQL Query Results (ALL 15)",
        "📈 Analytics", 
        "🍎 Food Listings", 
        "👥 Providers", 
        "🤝 Receivers", 
        "📋 Claims",
        "➕ Add Records",
        "✏️ Update Records",
        "🗑️ Delete Records"
    ]
    choice = st.sidebar.selectbox("Select an Option", menu)

    # Dashboard
    if choice == "🏠 Dashboard":
        st.header("📈 System Overview")
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            try:
                providers_count = pd.read_sql_query("SELECT COUNT(*) as count FROM providers", conn).iloc[0,0]
                st.metric("Total Providers", providers_count)
            except:
                st.metric("Total Providers", 0)
        
        with col2:
            try:
                receivers_count = pd.read_sql_query("SELECT COUNT(*) as count FROM receivers", conn).iloc[0,0]
                st.metric("Total Receivers", receivers_count)
            except:
                st.metric("Total Receivers", 0)
        
        with col3:
            try:
                food_count = pd.read_sql_query("SELECT COUNT(*) as count FROM food_listings", conn).iloc[0,0]
                st.metric("Food Listings", food_count)
            except:
                st.metric("Food Listings", 0)
        
        with col4:
            try:
                claims_count = pd.read_sql_query("SELECT COUNT(*) as count FROM claims", conn).iloc[0,0]
                st.metric("Total Claims", claims_count)
            except:
                st.metric("Total Claims", 0)

        # Recent activity
        st.subheader("📰 Recent Food Listings")
        try:
            recent_food = pd.read_sql_query("""
                SELECT Food_Name, Quantity, Location, Food_Type, Meal_Type 
                FROM food_listings 
                ORDER BY Food_ID DESC LIMIT 5
            """, conn)
            st.dataframe(recent_food, use_container_width=True)
        except:
            st.warning("⚠️ No recent food listings available")

        # Quick stats
        st.subheader("🎯 Quick Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                total_quantity = pd.read_sql_query("SELECT SUM(Quantity) as total FROM food_listings", conn).iloc[0,0]
                st.info(f"**Total Food Quantity Available:** {total_quantity:,} units" if total_quantity else "**Total Food Quantity Available:** 0 units")
            except:
                st.info("**Total Food Quantity Available:** 0 units")
        
        with col2:
            try:
                pending_claims = pd.read_sql_query("SELECT COUNT(*) as count FROM claims WHERE Status='Pending'", conn).iloc[0,0]
                st.warning(f"**Pending Claims:** {pending_claims}")
            except:
                st.warning("**Pending Claims:** 0")

    # SQL Query Results - THE MAIN SECTION WITH ALL 15 VISUALIZATIONS
    elif choice == "📊 SQL Query Results (ALL 15)":
        display_all_15_query_results()

    # Analytics
    elif choice == "📈 Analytics":
        st.header("📊 Data Analytics")
        
        tab1, tab2, tab3 = st.tabs(["Provider Analysis", "Claims Analysis", "Food Distribution"])
        
        with tab1:
            st.subheader("Provider Contribution Analysis")
            create_provider_chart()
            
        with tab2:
            st.subheader("Claims Status Analysis")
            create_claims_chart()
            
        with tab3:
            st.subheader("Food Type Distribution")
            create_food_type_chart()

    # Food Listings
    elif choice == "🍎 Food Listings":
        st.header("🍎 Available Food Listings")
        
        try:
            df_food = pd.read_sql_query("SELECT * FROM food_listings", conn)
            
            if not df_food.empty:
                # Filters
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    cities = df_food['Location'].unique().tolist()
                    city_filter = st.selectbox("Filter by City", ['All'] + cities)
                
                with col2:
                    food_types = df_food['Food_Type'].unique().tolist()
                    food_type_filter = st.selectbox("Filter by Food Type", ['All'] + food_types)
                
                with col3:
                    meal_types = df_food['Meal_Type'].unique().tolist()
                    meal_type_filter = st.selectbox("Filter by Meal Type", ['All'] + meal_types)

                # Apply filters
                filtered_df = df_food.copy()
                if city_filter != 'All':
                    filtered_df = filtered_df[filtered_df['Location'] == city_filter]
                if food_type_filter != 'All':
                    filtered_df = filtered_df[filtered_df['Food_Type'] == food_type_filter]
                if meal_type_filter != 'All':
                    filtered_df = filtered_df[filtered_df['Meal_Type'] == meal_type_filter]
                
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.warning("⚠️ No food listings available")
        except:
            st.error("❌ Error loading food listings")

    # Providers
    elif choice == "👥 Providers":
        st.header("👥 Food Providers")
        try:
            df_providers = pd.read_sql_query("SELECT * FROM providers", conn)
            st.dataframe(df_providers, use_container_width=True)
        except:
            st.warning("⚠️ No providers data available")

    # Receivers
    elif choice == "🤝 Receivers":
        st.header("🤝 Food Receivers")
        try:
            df_receivers = pd.read_sql_query("SELECT * FROM receivers", conn)
            st.dataframe(df_receivers, use_container_width=True)
        except:
            st.warning("⚠️ No receivers data available")

    # Claims
    elif choice == "📋 Claims":
        st.header("📋 Food Claims")
        try:
            df_claims = pd.read_sql_query("""
                SELECT c.Claim_ID, c.Food_ID, fl.Food_Name, c.Receiver_ID, 
                       r.Name as Receiver_Name, c.Status, c.Timestamp
                FROM claims c
                JOIN food_listings fl ON c.Food_ID = fl.Food_ID
                JOIN receivers r ON c.Receiver_ID = r.Receiver_ID
            """, conn)
            st.dataframe(df_claims, use_container_width=True)
        except:
            st.warning("⚠️ No claims data available")

    # Add Records
    elif choice == "➕ Add Records":
        st.header("➕ Add New Records")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Add Provider", "Add Receiver", "Add Food Listing", "Add Claim"])
        
        with tab1:
            st.subheader("Add New Provider")
            with st.form("add_provider"):
                provider_id = st.number_input("Provider ID", min_value=1, step=1)
                name = st.text_input("Provider Name")
                type_ = st.selectbox("Provider Type", ["Restaurant", "Grocery Store", "Supermarket", "Cafeteria"])
                address = st.text_input("Address")
                city = st.text_input("City")
                contact = st.text_input("Contact")
                
                if st.form_submit_button("Add Provider"):
                    try:
                        msg = insert_provider(provider_id, name, type_, address, city, contact)
                        st.success(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab2:
            st.subheader("Add New Receiver")
            with st.form("add_receiver"):
                receiver_id = st.number_input("Receiver ID", min_value=1, step=1)
                name = st.text_input("Receiver Name")
                type_ = st.selectbox("Receiver Type", ["NGO", "Community Center", "Individual"])
                city = st.text_input("City")
                contact = st.text_input("Contact")
                
                if st.form_submit_button("Add Receiver"):
                    try:
                        msg = insert_receiver(receiver_id, name, type_, city, contact)
                        st.success(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab3:
            st.subheader("Add New Food Listing")
            with st.form("add_food"):
                food_id = st.number_input("Food ID", min_value=1, step=1)
                food_name = st.text_input("Food Name")
                quantity = st.number_input("Quantity", min_value=1, step=1)
                expiry_date = st.date_input("Expiry Date")
                provider_id = st.number_input("Provider ID", min_value=1, step=1)
                provider_type = st.selectbox("Provider Type", ["Restaurant", "Grocery Store", "Supermarket", "Cafeteria"])
                location = st.text_input("Location (City)")
                food_type = st.selectbox("Food Type", ["Vegetarian", "Non-Vegetarian", "Vegan"])
                meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snacks"])
                
                if st.form_submit_button("Add Food Listing"):
                    try:
                        msg = insert_food_listing(food_id, food_name, quantity, expiry_date.strftime("%Y-%m-%d"), 
                                                provider_id, provider_type, location, food_type, meal_type)
                        st.success(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab4:
            st.subheader("Add New Claim")
            with st.form("add_claim"):
                claim_id = st.number_input("Claim ID", min_value=1, step=1)
                food_id = st.number_input("Food ID", min_value=1, step=1)
                receiver_id = st.number_input("Receiver ID", min_value=1, step=1)
                status = st.selectbox("Status", ["Pending", "Completed", "Cancelled"])
                timestamp = st.datetime_input("Claim Timestamp", datetime.now())
                
                if st.form_submit_button("Add Claim"):
                    try:
                        msg = insert_claim(claim_id, food_id, receiver_id, status, timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                        st.success(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")

    # Update Records
    elif choice == "✏️ Update Records":
        st.header("✏️ Update Records")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Update Provider", "Update Receiver", "Update Food Quantity", "Update Claim Status"])
        
        with tab1:
            st.subheader("Update Provider Contact")
            with st.form("update_provider"):
                provider_id = st.number_input("Provider ID", min_value=1, step=1)
                new_contact = st.text_input("New Contact")
                
                if st.form_submit_button("Update Provider Contact"):
                    try:
                        msg = update_provider_contact(provider_id, new_contact)
                        st.success(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab2:
            st.subheader("Update Receiver Contact")
            with st.form("update_receiver"):
                receiver_id = st.number_input("Receiver ID", min_value=1, step=1)
                new_contact = st.text_input("New Contact")
                
                if st.form_submit_button("Update Receiver Contact"):
                    try:
                        msg = update_receiver_contact(receiver_id, new_contact)
                        st.success(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab3:
            st.subheader("Update Food Quantity")
            with st.form("update_quantity"):
                food_id = st.number_input("Food ID", min_value=1, step=1)
                new_quantity = st.number_input("New Quantity", min_value=0, step=1)
                
                if st.form_submit_button("Update Quantity"):
                    try:
                        msg = update_food_quantity(food_id, new_quantity)
                        st.success(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab4:
            st.subheader("Update Claim Status")
            with st.form("update_status"):
                claim_id = st.number_input("Claim ID", min_value=1, step=1)
                new_status = st.selectbox("New Status", ["Pending", "Completed", "Cancelled"])
                
                if st.form_submit_button("Update Status"):
                    try:
                        msg = update_claim_status(claim_id, new_status)
                        st.success(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")

    # Delete Records
    elif choice == "🗑️ Delete Records":
        st.header("🗑️ Delete Records")
        st.warning("⚠️ **Warning:** Deletion is permanent and cannot be undone!")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Delete Provider", "Delete Receiver", "Delete Food Listing", "Delete Claim"])
        
        with tab1:
            st.subheader("Delete Provider")
            with st.form("delete_provider"):
                provider_id = st.number_input("Provider ID to Delete", min_value=1, step=1)
                confirm = st.checkbox("I confirm I want to delete this provider")
                
                if st.form_submit_button("Delete Provider"):
                    if confirm:
                        try:
                            msg = delete_provider(provider_id)
                            st.success(msg)
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Please confirm deletion by checking the checkbox")

        with tab2:
            st.subheader("Delete Receiver")
            with st.form("delete_receiver"):
                receiver_id = st.number_input("Receiver ID to Delete", min_value=1, step=1)
                confirm = st.checkbox("I confirm I want to delete this receiver")
                
                if st.form_submit_button("Delete Receiver"):
                    if confirm:
                        try:
                            msg = delete_receiver(receiver_id)
                            st.success(msg)
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Please confirm deletion by checking the checkbox")

        with tab3:
            st.subheader("Delete Food Listing")
            with st.form("delete_food"):
                food_id = st.number_input("Food ID to Delete", min_value=1, step=1)
                confirm = st.checkbox("I confirm I want to delete this record")
                
                if st.form_submit_button("Delete Food Listing"):
                    if confirm:
                        try:
                            msg = delete_food_listing(food_id)
                            st.success(msg)
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Please confirm deletion by checking the checkbox")

        with tab4:
            st.subheader("Delete Claim")
            with st.form("delete_claim"):
                claim_id = st.number_input("Claim ID to Delete", min_value=1, step=1)
                confirm = st.checkbox("I confirm I want to delete this record")
                
                if st.form_submit_button("Delete Claim"):
                    if confirm:
                        try:
                            msg = delete_claim(claim_id)
                            st.success(msg)
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Please confirm deletion by checking the checkbox")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🌱 Reducing Food Waste Together**")
    st.sidebar.markdown("*Built with Streamlit & SQLite*")

if __name__ == '__main__':
    main()
