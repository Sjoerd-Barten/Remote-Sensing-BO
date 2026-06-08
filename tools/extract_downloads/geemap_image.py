import ee
import os
import geemap
import rasterio
import numpy as np
from PIL import Image, ImageColor

from ee.featurecollection import FeatureCollection
from tools.Input_data.locaties import build_location_bound, RegionMode


# =========================================================
# DOWNLOAD IMAGE ALS GEOTIFF
# =========================================================
def download_single_geotiff(
    image: ee.Image,
    filename: str,
    locations_of_interest: FeatureCollection,
    coverage: RegionMode = "geometry",
    buffer_meters: int = 0,
    bands: list[str] | None = None,
    scale: int = 10,
) -> None:
    """
    Downloadt een ee.Image lokaal als GeoTIFF.

    Deze functie is bedoeld voor het opslaan van rasterdata
    met echte pixelwaarden, bijvoorbeeld:
    - NDVI
    - EVI
    - RGB banden
    - losse spectrale banden

    Het analysegebied wordt opgebouwd met build_location_bound(),
    zodat deze functie aansluit op de locatie-logica
    die al elders in de codebase wordt gebruikt.

    Parameters
    ----------
    image : ee.Image
        Het beeld dat moet worden gedownload.
    filename : str
        Bestandsnaam van de output, bijvoorbeeld:
        "output/ndvi_2020_06_15.tif"
    locations_of_interest : FeatureCollection
        De locaties die samen het downloadgebied bepalen.
    coverage : RegionMode, default "geometry"
        Bepaalt hoe het downloadgebied wordt opgebouwd.
    buffer_meters : int, default 0
        Extra buffer in meters rond het gebied.
        Alleen relevant als coverage="buffer".
    bands : list[str] | None, default None
        Optionele lijst met bandnamen die moeten worden geëxporteerd.
        Als None wordt opgegeven, blijven alle banden behouden.
    scale : int, default 10
        Resolutie in meters van de export.

    Returns
    -------
    None
    """

    # Zorg dat de outputmap bestaat.
    output_dir = os.path.dirname(filename)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Bouw het exportgebied op.
    region = build_location_bound(
        locations_of_interest=locations_of_interest,
        mode=coverage,
        buffer_meters=buffer_meters,
    )

    export_image = image

    # Selecteer optioneel een subset van de banden.
    if bands is not None:
        export_image = export_image.select(bands)

    # Clip het beeld op het gekozen gebied.
    export_image = export_image.clip(region)

    # Exporteer het beeld lokaal als GeoTIFF.
    geemap.ee_export_image(
        export_image,
        filename=filename,
        scale=scale,
        region=region,
        file_per_band=False,
    )

# =========================================================
# CONVERT GEOTIFF TO IMAGE
# =========================================================

def convert_geotiff_to_visual_image(
    tif_filename: str,
    output_filename: str,
    vis_params: dict,
    jpeg_quality: int = 95,
    transparent_nodata: bool = True,
) -> None:
    """
    Convert a single-band GeoTIFF to a visual PNG/JPG/JPEG using
    Earth-Engine-like vis_params.

    Supported vis_params keys:
    - min
    - max
    - palette

    Example:
    {
        "bands": ["NDVI"],
        "min": -1,
        "max": 1,
        "palette": ["red", "yellow", "green"]
    }
    """

    if not os.path.exists(tif_filename):
        raise FileNotFoundError(f"Input file not found: {tif_filename}")

    if "min" not in vis_params or "max" not in vis_params or "palette" not in vis_params:
        raise ValueError("vis_params must contain 'min', 'max', and 'palette'")

    vmin = float(vis_params["min"])
    vmax = float(vis_params["max"])
    palette = vis_params["palette"]

    if vmax <= vmin:
        raise ValueError("'max' must be greater than 'min'")

    output_dir = os.path.dirname(output_filename)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    _, ext = os.path.splitext(output_filename)
    output_format = ext.lower().lstrip(".")

    if output_format not in {"png", "jpg", "jpeg"}:
        raise ValueError("Output must end with .png, .jpg, or .jpeg")

    palette_rgb = np.array(
        [ImageColor.getrgb(color) for color in palette],
        dtype=np.float32,
    )

    with rasterio.open(tif_filename) as src:
        band = src.read(1).astype(np.float32)
        nodata = src.nodata

    mask = np.isnan(band)
    if nodata is not None:
        mask |= band == nodata

    # 1. Clamp to EE min/max
    band = np.clip(band, vmin, vmax)

    # 2. Scale to EE-style 8-bit display range [0..255]
    display = ((band - vmin) / (vmax - vmin)) * 255.0
    display = np.clip(display, 0, 255)

    # Optional: mimic EE display quantization more closely
    display_uint8 = np.rint(display).astype(np.uint8)

    # 3. Interpolate palette across 0..255
    scaled = display_uint8.astype(np.float32) / 255.0 * (len(palette_rgb) - 1)

    lower_idx = np.floor(scaled).astype(np.int32)
    upper_idx = np.ceil(scaled).astype(np.int32)

    lower_idx = np.clip(lower_idx, 0, len(palette_rgb) - 1)
    upper_idx = np.clip(upper_idx, 0, len(palette_rgb) - 1)

    fraction = (scaled - lower_idx)[..., np.newaxis]

    lower_colors = palette_rgb[lower_idx]
    upper_colors = palette_rgb[upper_idx]

    rgb = lower_colors + (upper_colors - lower_colors) * fraction
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    if output_format == "png" and transparent_nodata:
        alpha = np.where(mask, 0, 255).astype(np.uint8)
        rgba = np.dstack([rgb, alpha])
        image = Image.fromarray(rgba, mode="RGBA")
        image.save(output_filename, format="PNG")
    else:
        rgb[mask] = (0, 0, 0)
        image = Image.fromarray(rgb, mode="RGB")

        if output_format in {"jpg", "jpeg"}:
            image.save(output_filename, format="JPEG", quality=jpeg_quality)
        else:
            image.save(output_filename, format="PNG")