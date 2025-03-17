import streamlit as st
import pandas as pd
import boto3
import os
import datetime
from PIL import Image
import folium
from streamlit_folium import folium_static, st_folium

# Fetch environment variables
aws_access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
aws_default_region = 'us-east-2' #st.secrets["AWS_DEFAULT_REGION"]
BUCKET_NAME = "photoalbumclevlend"

# Initialize S3 Client
s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

# Function to upload files to S3
def upload_to_s3(file, file_name):
    try:
        s3.upload_fileobj(file, BUCKET_NAME, file_name, ExtraArgs={'ACL': 'public-read'})
        return f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}"
    except Exception as e:
        st.error(f"Error uploading to S3: {e}")
        return None

# Load or create database (CSV)
DB_FILE = "memories.csv"
if os.path.exists(DB_FILE):
    memories_df = pd.read_csv(DB_FILE)
else:
    memories_df = pd.DataFrame(columns=["Date", "Location", "Description", "Latitude", "Longitude", "File_URL"])

# App Title
st.title("📸 Travel Memory Journal with Interactive Map & S3")

# Sidebar for selecting or creating a memory
st.sidebar.subheader("🔍 Memory Selection")
memory_options = memories_df.apply(lambda row: f"{row['Location']} ({row['Date']})", axis=1).tolist()
selected_memory = st.sidebar.selectbox("Choose a saved memory or create new", ["Create New Memory"] + memory_options)

# Initialize empty variables for new memory
memory_index = None
date, location, description, latitude, longitude, file_url = None, "", "", 0.0, 0.0, ""

# Display selected memory or allow to create new memory
if selected_memory != "Create New Memory":
    memory_index = memory_options.index(selected_memory)
    memory_data = memories_df.iloc[memory_index]
    
    # Load existing data
    date = memory_data["Date"]
    location = memory_data["Location"]
    description = memory_data["Description"]
    latitude, longitude = memory_data["Latitude"], memory_data["Longitude"]
    file_url = memory_data["File_URL"]
    
    # Display existing memory
    st.markdown(f"### 📍 {location} ({date})")
    st.write(description if description else "No description available for this memory.")
    
    # Show photo/video
    if isinstance(file_url, str) and file_url.endswith((".jpg", ".png", ".jpeg")):
        st.image(file_url, use_column_width=True)
    elif isinstance(file_url, str) and file_url.endswith(".mp4"):
        st.video(file_url)

    # Show memory location on map
    st.subheader("📍 Memory Location")
    memory_map = folium.Map(location=[latitude, longitude], zoom_start=10)
    folium.Marker(
        [latitude, longitude],
        popup=f"{location} ({date})\n{description}"
    ).add_to(memory_map)
    folium_static(memory_map)

# Option to modify the selected memory or create a new one
if selected_memory == "Create New Memory" or memory_index is not None:
    st.subheader("✏️ Modify or Create New Memory")
    
    # Editable fields for existing or new memory
    date = st.date_input("Date of memory", datetime.datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.date.today())
    location = st.text_input("Location (e.g., Paris, France)", location if location else "")
    description = st.text_area("Write about this moment...", value=description, height=200)
    
    # Interactive map to select location
    st.subheader("🌍 Select Memory Location on Map")
    m = folium.Map(location=[latitude, longitude] if latitude and longitude else [48.8566, 2.3522], zoom_start=3)
    map_data = st_folium(m, height=350, width=700)
    
    # Extract clicked coordinates
    if map_data["last_clicked"]:
        latitude, longitude = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    
    st.write(f"📍 Selected Coordinates: {latitude}, {longitude}")
    
    # Upload file (Photo or Video)
    uploaded_file = st.file_uploader("Upload a Photo or Video", type=["jpg", "png", "jpeg", "mp4"])
    
    if uploaded_file:
        file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
        file_url = upload_to_s3(uploaded_file, file_name) or ""
        
        if uploaded_file.type.startswith("image"):
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Photo", use_column_width=True)
        elif uploaded_file.type.startswith("video"):
            st.video(file_url)
    
    if st.button("Save Memory"):
        if memory_index is not None:
            # Save the modified memory
            new_memory = pd.DataFrame([[date, location, description, latitude, longitude, file_url]], 
                                      columns=["Date", "Location", "Description", "Latitude", "Longitude", "File_URL"])
            memories_df.iloc[memory_index] = new_memory.iloc[0]  # Update the existing memory
            memories_df.to_csv(DB_FILE, index=False)
            st.success("Memory updated successfully!")
        else:
            # Save new memory
            new_memory = pd.DataFrame([[date, location, description, latitude, longitude, file_url]], 
                                      columns=["Date", "Location", "Description", "Latitude", "Longitude", "File_URL"])
            memories_df = pd.concat([memories_df, new_memory], ignore_index=True)
            memories_df.to_csv(DB_FILE, index=False)
            st.success("New memory saved successfully!")
