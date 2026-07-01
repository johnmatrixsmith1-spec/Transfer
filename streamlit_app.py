import streamlit as st
import os
import io
import ezdxf
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

def transform_dxf(input_dxf_bytes):
    """Convert DXF from ArmWGS84 to WGS84 coordinates"""
    # Read input DXF from bytes using ezdxf.read()
    dxf = ezdxf.read(io.BytesIO(input_dxf_bytes))
    
    # Create new DXF with transformed entities
    new_dxf = ezdxf.new('R2010')
    new_msp = new_dxf.modelspace()
    
    old_msp = dxf.modelspace()
    entity_count = 0
    
    for entity in old_msp:
        try:
            if entity.dxftype() == 'POINT':
                x, y, z = entity.dxf.location
                new_x, new_y, new_z = transform_point(x, y, z)
                new_msp.add_point((new_x, new_y, new_z))
                entity_count += 1
                
            elif entity.dxftype() == 'LINE':
                p1 = entity.dxf.start
                p2 = entity.dxf.end
                new_p1 = transform_point(p1.x, p1.y, p1.z)
                new_p2 = transform_point(p2.x, p2.y, p2.z)
                new_msp.add_line(new_p1, new_p2)
                entity_count += 1
                
            elif entity.dxftype() == 'LWPOLYLINE':
                points = []
                for x, y, *rest in entity.get_points(as_tuple=True):
                    z = rest[0] if rest else 0
                    new_x, new_y, new_z = transform_point(x, y, z)
                    points.append((new_x, new_y))
                if len(points) > 1:
                    new_msp.add_lwpolyline(points)
                    entity_count += 1
                    
            elif entity.dxftype() == 'POLYLINE':
                points = []
                for vertex in entity.points:
                    x, y, z = vertex.dxf.location
                    new_x, new_y, new_z = transform_point(x, y, z)
                    points.append((new_x, new_y))
                if len(points) > 1:
                    new_msp.add_lwpolyline(points)
                    entity_count += 1
                    
            elif entity.dxftype() == 'CIRCLE':
                cx, cy, cz = entity.dxf.center
                new_cx, new_cy, new_cz = transform_point(cx, cy, cz)
                radius = entity.dxf.radius
                new_msp.add_circle((new_cx, new_cy, new_cz), radius)
                entity_count += 1
        except Exception as e:
            st.warning(f"Could not transform entity {entity.dxftype()}: {str(e)}")
            continue
    
    return new_dxf, entity_count

# --- Streamlit Web Interface ---
st.set_page_config(page_title="DXF Coordinate Translator", page_icon="🗺️")
st.title("🗺️ DXF Coordinate Translator")
st.write("Convert DXF coordinates from **ArmWGS84** (projected) to **WGS84** (geographic lat/lon)")

uploaded_file = st.file_uploader("Choose a DXF file (ArmWGS84)", type=["dxf"])

if uploaded_file is not None:
    try:
        # Read uploaded DXF
        dxf_bytes = uploaded_file.read()
        
        # Transform coordinates
        new_dxf, entity_count = transform_dxf(dxf_bytes)
        
        if entity_count == 0:
            st.warning("⚠️ No compatible entities found in the DXF file!")
        else:
            # Save to temporary file
            output_filename = uploaded_file.name.replace('.dxf', '_WGS84.dxf')
            new_dxf.saveas(output_filename)
            
            with open(output_filename, "rb") as file:
                st.success(f"🎉 Conversion successful! Transformed {entity_count} entities.")
                st.download_button(
                    label="📥 Download WGS84 DXF File",
                    data=file,
                    file_name=output_filename,
                    mime="application/dxf"
                )
            
            # Clean up backend file
            os.remove(output_filename)
    
    except Exception as e:
        st.error(f"❌ Error during conversion: {str(e)}")
