"""Pakistan's country > province > city hierarchy with a search area per city.

Coordinates are city-centre approximations and radius_km is the search radius. They are
starting values: adjust them from the Geographies screen if a city's search area is off.
"""

COUNTRY = "Pakistan"

# province -> [(city, latitude, longitude, radius_km), ...]
# Islamabad Capital Territory is a federal territory, listed alongside the provinces.
REGIONS: dict[str, list[tuple[str, float, float, float]]] = {
    "Punjab": [
        ("Lahore", 31.5204, 74.3587, 20),
        ("Faisalabad", 31.4504, 73.1350, 12),
        ("Rawalpindi", 33.5651, 73.0169, 12),
        ("Multan", 30.1575, 71.5249, 12),
        ("Gujranwala", 32.1877, 74.1945, 10),
        ("Sialkot", 32.4945, 74.5229, 10),
        ("Bahawalpur", 29.3956, 71.6836, 10),
        ("Sargodha", 32.0836, 72.6711, 10),
        ("Sahiwal", 30.6682, 73.1114, 8),
        ("Sheikhupura", 31.7131, 73.9783, 8),
        ("Gujrat", 32.5731, 74.0789, 8),
        ("Jhang", 31.2681, 72.3181, 8),
        ("Rahim Yar Khan", 28.4202, 70.2952, 8),
        ("Dera Ghazi Khan", 30.0561, 70.6348, 8),
        ("Kasur", 31.1187, 74.4500, 8),
        ("Okara", 30.8138, 73.4534, 8),
    ],
    "Sindh": [
        ("Karachi", 24.8607, 67.0011, 30),
        ("Hyderabad", 25.3960, 68.3578, 12),
        ("Sukkur", 27.7052, 68.8574, 8),
        ("Larkana", 27.5570, 68.2028, 8),
        ("Nawabshah", 26.2483, 68.4096, 8),
        ("Mirpur Khas", 25.5276, 69.0111, 8),
    ],
    "Khyber Pakhtunkhwa": [
        ("Peshawar", 34.0151, 71.5249, 15),
        ("Mardan", 34.1989, 72.0400, 8),
        ("Abbottabad", 34.1688, 73.2215, 8),
        ("Mingora", 34.7717, 72.3600, 8),
        ("Kohat", 33.5869, 71.4414, 8),
        ("Dera Ismail Khan", 31.8626, 70.9019, 8),
        ("Bannu", 32.9889, 70.6056, 8),
    ],
    "Balochistan": [
        ("Quetta", 30.1798, 66.9750, 15),
        ("Hub", 25.0431, 66.9066, 10),
        ("Gwadar", 25.1216, 62.3254, 10),
        ("Khuzdar", 27.8000, 66.6100, 8),
        ("Turbat", 26.0012, 63.0544, 8),
        ("Sibi", 29.5430, 67.8773, 6),
    ],
    "Islamabad Capital Territory": [
        ("Islamabad", 33.6844, 73.0479, 15),
    ],
}
