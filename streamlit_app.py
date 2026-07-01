import streamlit as st
import os
import zipfile
from fastkml import kml
import ezdxf
from pyproj import CRS, Transformer

# Define projection math
SRC_WKT = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
DST_WKT = 'PROJCS["ArmWGS84_Final_Precision",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",8500001.4849],PARAMETER["False_Northing",77.1551],PARAMETER["Central_Meridian",45.0],PARAMETER["Scale_Factor",1.0],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'

transformer = Transformer.from_crs(CRS.from_wkt(SRC_WKT), CRS.from_wkt(DST_WKT), always_xy=True)

def process_geometry(geom, msp):
    if geom.geom_type == 'Point':
        x, y = transformer.transform(geom.x, geom.y)
        z = geom.z if geom.has_z else 0.0
        msp.add_point((x, y, z))
    elif geom.geom_type == 'LineString':
        projected_coords = []
        for x, y, *z in geom.coords:
            nx, ny = transformer.transform(x, y)
            nz = z[0] if z else 0.0
            projected_coords.append((nx, ny, nz))
        msp.add_lwpolyline([(p[0], p[1]) for p in projected_coords]) 
    elif geom.geom_type == 'Polygon':
        projected_coords = []
        for x, y, *z in geom.exterior.coords:
            nx, ny = transformer.transform(x, y)
            nz = z[0] if z else 0.0
            projected_coords.append((nx, ny, nz))
        msp.add_lwpolyline([(p[0], p[1]) for p in projected_coords], dxfattribs={'flags': 1})

def deconstruct_features(features, msp):
    for feature in features:
        if hasattr(feature, 'features'):
            deconstruct_features(feature.features, msp)
        if hasattr(feature, 'geometry') and feature.geometry is not None:
            process_geometry(feature.geometry, msp)

# --- Streamlit Web Interface ---
st.set_page_config(page_title="KMZ to DXF Converter", page_icon="🌍")
st.title("🌍 KMZ to ArmWGS84 DXF Converter")
st.write("Upload a Google Earth `.kmz` file to reproject its geometry into the **ArmWGS84 Final Precision (meters)** coordinate system.")

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
        deconstruct_features(k.features(), msp)

        # Save to a temporary file path to stream back to user
        output_filename = uploaded_file.name.replace('.kmz', '_projected.dxf')
        doc.saveas(output_filename)

        with open(output_filename, "rb") as file:
            st.success("🎉 Conversion successful!")
            st.download_button(
                label="📥 Download Projected DXF File",
                data=file,
                file_name=output_filename,
                mime="application/dxf"
            )
            
        # Clean up backend file
        os.remove(output_filename)

    except Exception as e:
        st.error(f"An error occurred during conversion: {str(e)}")
