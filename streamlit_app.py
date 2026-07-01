import streamlit as st
import os
import io
from pyproj import CRS, Transformer

# --- Coordinate System Definitions ---
# ArmWGS84 Final Precision (projected coordinates in meters)
ARMWGS84_WKT = 'PROJCS["ArmWGS84_Final_Precision",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",8500001.4849],PARAMETER["False_Northing",77.1551],PARAMETER["Central_Meridian",45.0],PARAMETER["Scale_Factor",1.0],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'

# WGS84 Geographic (lat/lon)
WGS84_WKT = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'

# Create transformer: ArmWGS84 → WGS84
transformer = Transformer.from_crs(
    CRS.from_wkt(ARMWGS84_WKT), 
    CRS.from_wkt(WGS84_WKT), 
    always_xy=True
)

def transform_point(x, y, z=0):
    """Transform a single point from ArmWGS84 to WGS84"""
    lon, lat = transformer.transform(x, y)
    return lon, lat, z

def parse_str_file(content):
    """Parse Surpac .str file content"""
    lines = content.strip().split('\n')
    features = []
    current_feature = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('!'):
            continue
        
        # Check for feature header (typically starts with a letter indicating type)
        parts = line.split()
        if len(parts) >= 2:
            try:
                # Try to parse as coordinates
                x = float(parts[0])
                y = float(parts[1])
                z = float(parts[2]) if len(parts) > 2 else 0
                
                if current_feature is None:
                    current_feature = {'points': []}
                
                current_feature['points'].append((x, y, z))
            except ValueError:
                # Line is not coordinates, might be a feature marker
                if current_feature is not None and current_feature['points']:
                    features.append(current_feature)
                current_feature = {'points': []}
    
    # Add last feature
    if current_feature is not None and current_feature['points']:
        features.append(current_feature)
    
    return features

def transform_str_file(input_str_content):
    """Convert .str file from ArmWGS84 to WGS84 coordinates"""
    features = parse_str_file(input_str_content)
    
    output_lines = []
    entity_count = 0
    
    for feature in features:
        transformed_points = []
        for x, y, z in feature['points']:
            new_x, new_y, new_z = transform_point(x, y, z)
            transformed_points.append((new_x, new_y, new_z))
            entity_count += 1
        
        # Write transformed feature
        for new_x, new_y, new_z in transformed_points:
            output_lines.append(f"{new_x:.8f} {new_y:.8f} {new_z:.8f}")
        output_lines.append("")  # Blank line between features
    
    return "\n".join(output_lines), entity_count

# --- Streamlit Web Interface ---
st.set_page_config(page_title="Surpac STR Coordinate Translator", page_icon="🗺️")
st.title("🗺️ Surpac STR Coordinate Translator")
st.write("Convert Surpac .str coordinates from **ArmWGS84** (projected) to **WGS84** (geographic lat/lon)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Upload .str File")
    uploaded_file = st.file_uploader("Choose a .str file (ArmWGS84)", type=["str", "txt"])

with col2:
    st.subheader("Or Paste Content")
    pasted_content = st.text_area("Paste .str file content:", height=200)

if uploaded_file is not None or pasted_content:
    try:
        # Get input content
        if uploaded_file is not None:
            input_content = uploaded_file.read().decode('utf-8')
            input_filename = uploaded_file.name
        else:
            input_content = pasted_content
            input_filename = "converted_coords.str"
        
        # Transform coordinates
        output_content, entity_count = transform_str_file(input_content)
        
        if entity_count == 0:
            st.warning("⚠️ No coordinates found in the file!")
        else:
            st.success(f"🎉 Conversion successful! Transformed {entity_count} coordinates.")
            
            # Display preview
            st.subheader("Preview (first 10 lines):")
            preview_lines = output_content.split('\n')[:10]
            st.code('\n'.join(preview_lines), language='text')
            
            # Download button
            output_filename = input_filename.replace('.str', '_WGS84.str').replace('.txt', '_WGS84.str')
            st.download_button(
                label="📥 Download WGS84 STR File",
                data=output_content,
                file_name=output_filename,
                mime="text/plain"
            )
    
    except Exception as e:
        st.error(f"❌ Error during conversion: {str(e)}")
