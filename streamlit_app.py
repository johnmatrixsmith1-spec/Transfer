import streamlit as st
import os
import zipfile
from fastkml import kml
import ezdxf

# --- Streamlit Web Interface ---
st.set_page_config(page_title="KMZ to DXF Converter", page_icon="🌍")
st.title("🌍 KMZ to DXF Converter")
st.write("Upload a Google Earth `.kmz` file to convert it to DXF format.")

uploaded_file = st.file_uploader("Choose a KMZ file", type=["kmz"])

if uploaded_file is not None:
    try:
        # Process file entirely in memory
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            kml_filename = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_filename) as kml_file:
                kml_data = kml_file.read()

        k = kml.KML()
        k.from_string(kml_data)

        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        geometry_count = 0

        # Recursively extract geometries from document and folders
        def extract_geometries(features):
            global geometry_count
            for feature in features:
                # Handle folders (Folder elements contain more features)
                if hasattr(feature, 'features'):
                    extract_geometries(feature.features)
                
                # Handle placemarks with geometry
                if hasattr(feature, 'geometry') and feature.geometry is not None:
                    geom = feature.geometry
                    
                    if geom.geom_type == 'Point':
                        x, y = geom.x, geom.y
                        z = geom.z if geom.has_z else 0.0
                        msp.add_point((x, y, z))
                        geometry_count += 1
                        
                    elif geom.geom_type == 'LineString':
                        coords = [(p[0], p[1]) for p in geom.coords]
                        if len(coords) > 1:
                            msp.add_lwpolyline(coords)
                            geometry_count += 1
                            
                    elif geom.geom_type == 'Polygon':
                        coords = [(p[0], p[1]) for p in geom.exterior.coords]
                        if len(coords) > 2:
                            msp.add_lwpolyline(coords, dxfattribs={'flags': 1})
                            geometry_count += 1

        extract_geometries(k.features)

        if geometry_count == 0:
            st.warning("⚠️ No geometries found in the KMZ file!")
        else:
            # Save to temporary file
            output_filename = uploaded_file.name.replace('.kmz', '.dxf')
            doc.saveas(output_filename)

            with open(output_filename, "rb") as file:
                st.success(f"🎉 Conversion successful! Found {geometry_count} geometries.")
                st.download_button(
                    label="📥 Download DXF File",
                    data=file,
                    file_name=output_filename,
                    mime="application/dxf"
                )
                
            # Clean up backend file
            os.remove(output_filename)

    except Exception as e:
        st.error(f"An error occurred during conversion: {str(e)}")
